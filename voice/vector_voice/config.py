"""Voice-client configuration, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VoiceConfig:
    server_url: str = "http://localhost:8000"
    wake_word: str = "vector"
    session_id: str = "voice"

    # Backend selection: "console" runs with no audio hardware.
    wake_backend: str = "console"  # console | openwakeword | porcupine
    stt_backend: str = "console"  # console | whisper
    tts_backend: str = "console"  # console | piper | pyttsx3

    @classmethod
    def from_env(cls) -> VoiceConfig:
        return cls(
            server_url=os.getenv("VECTOR_SERVER_URL", cls.server_url),
            wake_word=os.getenv("VECTOR_WAKE_WORD", cls.wake_word),
            session_id=os.getenv("VECTOR_VOICE_SESSION", cls.session_id),
            wake_backend=os.getenv("VECTOR_WAKE_BACKEND", cls.wake_backend),
            stt_backend=os.getenv("VECTOR_STT_BACKEND", cls.stt_backend),
            tts_backend=os.getenv("VECTOR_TTS_BACKEND", cls.tts_backend),
        )
