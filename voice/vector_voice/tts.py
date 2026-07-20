"""Text-to-speech.

:class:`ConsoleTTS` prints the reply. :class:`PyttsxTTS` speaks it aloud with
the cross-platform `pyttsx3` engine if installed.
"""

from __future__ import annotations

from typing import Protocol


class TextToSpeech(Protocol):
    def speak(self, text: str) -> None: ...


class ConsoleTTS:
    def speak(self, text: str) -> None:
        print(f"vector> {text}")


class PyttsxTTS:
    """Offline TTS via `pyttsx3` (requires the `tts` extra)."""

    def __init__(self) -> None:
        import pyttsx3  # lazy import

        self._engine = pyttsx3.init()

    def speak(self, text: str) -> None:  # pragma: no cover - requires audio out
        print(f"vector> {text}")
        self._engine.say(text)
        self._engine.runAndWait()


def build(backend: str) -> TextToSpeech:
    if backend in ("pyttsx3", "piper"):
        try:
            return PyttsxTTS()
        except Exception:
            pass
    return ConsoleTTS()
