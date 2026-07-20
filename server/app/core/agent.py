"""The VECTOR agent — reason, plan, act.

The agent is the orchestrator described in the architecture diagram. For each
incoming command it:

1. records the message in memory,
2. asks the planner to decompose it into steps,
3. executes every step through the matching capability
   (conversation, home automation, robot, arm, vision, ...),
4. composes a natural-language reply and stores it.

Executors publish to the message bus; the physical work happens in the robots,
firmware and smart-home devices that subscribe to those topics.
"""

from __future__ import annotations

import logging
import re

from app.core.home_automation import HomeAutomation
from app.core.llm import LLMProvider
from app.core.memory import InMemoryMemory
from app.core.planner import HeuristicPlanner
from app.core.robot_manager import RobotManager
from app.models.schemas import (
    ArmCommand,
    AssistantCommand,
    AssistantReply,
    Capability,
    HomeDeviceCommand,
    PlanStep,
    RobotCommand,
    StepStatus,
)

logger = logging.getLogger("vector.agent")

SYSTEM_PROMPT = (
    "You are VECTOR, a helpful personal robotics and home assistant. "
    "Be concise, friendly and action-oriented."
)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "please",
    "turn",
    "switch",
    "set",
    "my",
    "to",
    "on",
    "off",
    "in",
    "of",
    "at",
    "for",
}


class Agent:
    def __init__(
        self,
        llm: LLMProvider,
        memory: InMemoryMemory,
        planner: HeuristicPlanner,
        robots: RobotManager,
        home: HomeAutomation,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._planner = planner
        self._robots = robots
        self._home = home

    async def handle(self, command: AssistantCommand) -> AssistantReply:
        session = command.session_id
        self._memory.add_message(session, "user", command.text)

        plan = self._planner.plan(command.text)
        for step in plan.steps:
            step.status = StepStatus.RUNNING
            try:
                step.result = await self._execute(step, session)
                step.status = StepStatus.DONE
            except Exception as exc:  # keep going; report per-step failure
                logger.exception("step %s failed", step.id)
                step.result = f"failed: {exc}"
                step.status = StepStatus.FAILED

        reply_text = self._compose(plan.steps)
        self._memory.add_message(session, "assistant", reply_text)
        return AssistantReply(text=reply_text, session_id=session, plan=plan)

    # -- step execution ---------------------------------------------------
    async def _execute(self, step: PlanStep, session: str) -> str:
        match step.capability:
            case Capability.CONVERSATION:
                context = self._memory.transcript(session)
                return await self._llm.complete(SYSTEM_PROMPT, context or step.description)

            case Capability.HOME_AUTOMATION:
                device_id, cmd = _parse_home(step.description)
                self._home.command(device_id, cmd)
                return f"{cmd.action} {device_id.replace('-', ' ')}"

            case Capability.ROBOT:
                cmd = _parse_robot(step.description)
                self._robots.dispatch("mobile-1", cmd)
                return f"dispatched robot to {cmd.action}"

            case Capability.ROBOT_ARM:
                cmd = ArmCommand(action="pick", target={"query": step.description})
                self._robots.dispatch_arm(cmd)
                return f"arm handling: {step.description}"

            case Capability.VISION:
                return "checking the camera feed"

            case Capability.REMINDER:
                self._memory.remember(f"reminder:{step.id}", step.description)
                return f"reminder noted: {step.description}"

            case Capability.SEARCH:
                return f"searching for: {step.description}"

        return "done"

    def _compose(self, steps: list[PlanStep]) -> str:
        if len(steps) == 1:
            return steps[0].result or "Done."
        lines = [f"- {s.result}" for s in steps if s.result]
        return "Here's what I did:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Lightweight clause parsers (used by the offline/heuristic path)
# ---------------------------------------------------------------------------
def _slug(text: str) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]
    return "-".join(words) or "device"


def _parse_home(clause: str) -> tuple[str, HomeDeviceCommand]:
    lowered = clause.lower()
    if "off" in lowered:
        action = "off"
    elif "on" in lowered:
        action = "on"
    else:
        action = "set"
    device_id = _slug(clause)
    return device_id, HomeDeviceCommand(action=action)


def _parse_robot(clause: str) -> RobotCommand:
    lowered = clause.lower()
    if any(w in lowered for w in ("clean", "vacuum")):
        return RobotCommand(action="clean", params={"request": clause})
    if any(w in lowered for w in ("bring", "fetch", "deliver")):
        return RobotCommand(action="deliver", params={"request": clause})
    return RobotCommand(action="navigate", params={"request": clause})
