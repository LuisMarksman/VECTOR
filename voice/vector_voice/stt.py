"""Speech-to-text.

:class:`ConsoleSTT` reads a line from stdin so the pipeline works without a
microphone. :class:`WhisperSTT` shows where a real recogniser plugs in.
"""

from __future__ import annotations

from typing import Protocol


class SpeechToText(Protocol):
    def transcribe(self) -> str:
        """Capture one utterance and return the recognised text."""
        ...


class ConsoleSTT:
    """Type what you would have said."""

    def transcribe(self) -> str:
        return input("you> ").strip()


class WhisperSTT:
    """faster-whisper backend (requires the `whisper` extra + a mic).

    Skeleton: record a short clip from the microphone, then transcribe it.
    """

    def __init__(self, model_size: str = "base") -> None:
        from faster_whisper import WhisperModel  # lazy import

        self._model = WhisperModel(model_size)

    def transcribe(self) -> str:  # pragma: no cover - requires audio hardware
        raise NotImplementedError(
            "Record microphone audio to a buffer/file and pass it to "
            "self._model.transcribe(); join the returned segments."
        )


def build(backend: str) -> SpeechToText:
    if backend == "whisper":
        return WhisperSTT()
    return ConsoleSTT()
