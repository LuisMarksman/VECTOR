"""The voice assistant pipeline."""

from __future__ import annotations

import logging

import httpx

from vector_voice import stt as stt_mod
from vector_voice import tts as tts_mod
from vector_voice import wake_word as wake_mod
from vector_voice.client import VectorClient
from vector_voice.config import VoiceConfig

logger = logging.getLogger("vector.voice")


class VoiceAssistant:
    """Wires the wake word, STT, server client and TTS into a loop."""

    def __init__(self, config: VoiceConfig | None = None) -> None:
        self.config = config or VoiceConfig.from_env()
        self.wake = wake_mod.build(self.config.wake_backend, self.config.wake_word)
        self.stt = stt_mod.build(self.config.stt_backend)
        self.tts = tts_mod.build(self.config.tts_backend)
        self.client = VectorClient(self.config.server_url, self.config.session_id)

    def run(self) -> None:
        self.tts.speak(f"{self.config.wake_word} is ready.")
        try:
            while True:
                self.wake.wait()
                text = self.stt.transcribe()
                if not text:
                    continue
                if text.lower() in {"quit", "exit", "stop"}:
                    break
                self._handle(text)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.client.close()
            self.tts.speak("Goodbye.")

    def _handle(self, text: str) -> None:
        try:
            reply = self.client.send(text)
        except httpx.HTTPError as exc:
            logger.error("server error: %s", exc)
            self.tts.speak("Sorry, I couldn't reach the VECTOR server.")
            return
        self.tts.speak(reply)
