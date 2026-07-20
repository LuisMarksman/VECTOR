from __future__ import annotations

from app.core.memory import InMemoryMemory


def test_history_roundtrip():
    mem = InMemoryMemory()
    mem.add_message("s", "user", "hi")
    mem.add_message("s", "assistant", "hello")
    history = mem.history("s")
    assert [m.role for m in history] == ["user", "assistant"]


def test_transcript_limit():
    mem = InMemoryMemory()
    for i in range(20):
        mem.add_message("s", "user", f"m{i}")
    transcript = mem.transcript("s", limit=5)
    assert transcript.count("\n") == 4  # 5 lines -> 4 newlines


def test_facts():
    mem = InMemoryMemory()
    mem.remember("owner", "Parth")
    assert mem.recall("owner") == "Parth"
    assert mem.recall("missing") is None
