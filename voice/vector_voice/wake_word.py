"""Wake-word detection.

The default :class:`ConsoleWakeWord` simply waits for the user to press Enter,
so the pipeline is usable with no audio hardware. Real detectors implement the
same :meth:`wait` method.
"""

from __future__ import annotations

from typing import Protocol


class WakeWordDetector(Protocol):
    def wait(self) -> None:
        """Block until the wake word is detected."""
        ...


class ConsoleWakeWord:
    """Press Enter to 'wake' VECTOR — no microphone required."""

    def __init__(self, wake_word: str = "vector") -> None:
        self.wake_word = wake_word

    def wait(self) -> None:
        input(f"[press Enter to talk to {self.wake_word}] ")


class OpenWakeWord:
    """openWakeWord-based detector (requires the `openwakeword` extra).

    This is a thin skeleton showing where the real streaming detection loop
    goes; wire it to your microphone stream (e.g. via `sounddevice`).
    """

    def __init__(self, wake_word: str = "vector") -> None:
        from openwakeword.model import Model  # lazy import

        self.wake_word = wake_word
        self._model = Model()

    def wait(self) -> None:  # pragma: no cover - requires audio hardware
        raise NotImplementedError(
            "Stream microphone audio into self._model.predict() and return "
            "when the wake-word score crosses your threshold."
        )


def build(backend: str, wake_word: str) -> WakeWordDetector:
    if backend == "openwakeword":
        return OpenWakeWord(wake_word)
    return ConsoleWakeWord(wake_word)
