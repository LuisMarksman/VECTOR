"""The main assistant endpoint — send a command, get a planned reply."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ServicesDep
from app.models.schemas import AssistantCommand, AssistantReply

router = APIRouter()


@router.post("/command", response_model=AssistantReply)
async def command(payload: AssistantCommand, services: ServicesDep) -> AssistantReply:
    """Handle a natural-language command end to end (plan + execute)."""
    return await services.agent.handle(payload)


@router.get("/history/{session_id}")
def history(session_id: str, services: ServicesDep) -> dict:
    """Return the recent conversation transcript for a session."""
    messages = services.memory.history(session_id)
    return {
        "session_id": session_id,
        "messages": [{"role": m.role, "text": m.text} for m in messages],
    }
