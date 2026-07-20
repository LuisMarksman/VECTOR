"""Conversation history and long-term memory.

The default :class:`InMemoryMemory` keeps everything in process — perfect for
development and tests. A persistent SQLite/Postgres backend can implement the
same small surface (``add_message``/``history``/``remember``/``recall``)
without touching the agent.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "user" | "assistant"
    text: str


class InMemoryMemory:
    """Bounded per-session history plus a simple key/value fact store."""

    def __init__(self, max_history: int = 50) -> None:
        self._history: dict[str, deque[Message]] = defaultdict(lambda: deque(maxlen=max_history))
        self._facts: dict[str, str] = {}

    # -- conversation -----------------------------------------------------
    def add_message(self, session_id: str, role: str, text: str) -> None:
        self._history[session_id].append(Message(role=role, text=text))

    def history(self, session_id: str) -> list[Message]:
        return list(self._history.get(session_id, ()))

    def transcript(self, session_id: str, limit: int = 10) -> str:
        """Render the recent history as a prompt-friendly transcript."""
        recent = self.history(session_id)[-limit:]
        return "\n".join(f"{m.role}: {m.text}" for m in recent)

    def clear(self, session_id: str) -> None:
        self._history.pop(session_id, None)

    # -- long-term facts --------------------------------------------------
    def remember(self, key: str, value: str) -> None:
        self._facts[key] = value

    def recall(self, key: str) -> str | None:
        return self._facts.get(key)

    def all_facts(self) -> dict[str, str]:
        return dict(self._facts)
