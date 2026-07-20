"""Request/response and domain schemas for the VECTOR API.

These models are the contract between the server and every client — the voice
assistant, the web/mobile UI, robots and smart-home devices.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------
class Capability(StrEnum):
    """High-level capabilities the planner can route a step to."""

    CONVERSATION = "conversation"
    HOME_AUTOMATION = "home_automation"
    ROBOT = "robot"
    ROBOT_ARM = "robot_arm"
    VISION = "vision"
    REMINDER = "reminder"
    SEARCH = "search"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class PlanStep(BaseModel):
    """A single actionable step produced by the planner."""

    id: int
    description: str
    capability: Capability = Capability.CONVERSATION
    params: dict = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: str | None = None


class Plan(BaseModel):
    """An ordered set of steps that fulfils a user goal."""

    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class AssistantCommand(BaseModel):
    """A natural-language command from a user."""

    text: str = Field(..., min_length=1, examples=["Turn on the living room lights"])
    session_id: str = Field(default="default", description="Conversation/session identifier")


class AssistantReply(BaseModel):
    """The assistant's response, including the plan it executed."""

    text: str
    session_id: str
    plan: Plan | None = None


# ---------------------------------------------------------------------------
# Robots
# ---------------------------------------------------------------------------
class RobotCommand(BaseModel):
    action: str = Field(..., examples=["navigate", "dock", "stop"])
    params: dict = Field(default_factory=dict)


class RobotState(BaseModel):
    robot_id: str
    online: bool = False
    battery: float | None = Field(default=None, ge=0, le=100)
    pose: dict | None = None
    status: str = "idle"


class ArmCommand(BaseModel):
    action: str = Field(..., examples=["pick", "place", "home"])
    target: dict | None = Field(default=None, description="Target object or coordinates")


# ---------------------------------------------------------------------------
# Smart home
# ---------------------------------------------------------------------------
class HomeDeviceCommand(BaseModel):
    action: str = Field(..., examples=["on", "off", "set"])
    value: float | str | bool | None = None


class HomeDeviceState(BaseModel):
    device_id: str
    kind: str = "generic"  # light | switch | sensor | camera ...
    online: bool = False
    state: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------
class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    box: BoundingBox | None = None


class VisionEvent(BaseModel):
    source: str = "camera0"
    detections: list[Detection] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------
class HealthStatus(BaseModel):
    status: str = "ok"
    service: str = "vector-server"
    version: str = "0.1.0"
    environment: str = "development"
    mqtt_connected: bool = False
