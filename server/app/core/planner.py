"""Turn a natural-language command into an executable :class:`Plan`.

The default :class:`HeuristicPlanner` uses keyword routing so VECTOR does
something sensible with **no** LLM configured — it splits a request on
conjunctions ("and", "then", ...) and routes each clause to a capability.
When an LLM backend is enabled it can produce richer, structured plans; the
heuristic layer remains a reliable fallback.
"""

from __future__ import annotations

import re

from app.models.schemas import Capability, Plan, PlanStep

# Keyword -> capability routing table. Order matters: earlier, more specific
# intents win over generic ones.
_ROUTES: list[tuple[Capability, tuple[str, ...]]] = [
    (Capability.ROBOT_ARM, ("pick", "place", "grab", "grasp", "hand me", "put down")),
    (Capability.ROBOT, ("bring", "fetch", "deliver", "go to", "navigate", "clean", "vacuum")),
    (
        Capability.HOME_AUTOMATION,
        ("light", "lamp", "switch", "plug", "thermostat", "fan", "ac ", "turn on", "turn off"),
    ),
    (Capability.VISION, ("see", "look", "detect", "recognize", "who is", "what is in")),
    (Capability.REMINDER, ("remind", "reminder", "schedule", "alarm", "calendar")),
    (Capability.SEARCH, ("search", "look up", "google", "what is", "who is", "weather")),
]

_SPLIT = re.compile(r"\s*(?:,|\band then\b|\bthen\b|\band\b)\s+", flags=re.IGNORECASE)


def _classify(clause: str) -> Capability:
    lowered = clause.lower()
    for capability, keywords in _ROUTES:
        if any(keyword in lowered for keyword in keywords):
            return capability
    return Capability.CONVERSATION


class HeuristicPlanner:
    """Rule-based planner — deterministic and dependency-free."""

    def plan(self, text: str) -> Plan:
        clauses = [c.strip() for c in _SPLIT.split(text) if c.strip()]
        if not clauses:
            clauses = [text.strip()]
        steps = [
            PlanStep(id=i, description=clause, capability=_classify(clause))
            for i, clause in enumerate(clauses, start=1)
        ]
        return Plan(goal=text.strip(), steps=steps)
