"""Configuration for the VECTOR voice server.

Everything is read from the environment so the same image runs unchanged on a
laptop and on the Raspberry Pi. See .env.example for the full list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    return int(raw) if raw else default


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


@dataclass
class Config:
    # --- server ---------------------------------------------------------
    host: str = field(default_factory=lambda: _env("VECTOR_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("VECTOR_PORT", 8000))
    # Advertised to the device in the OTA response. Must be reachable *from the
    # ESP32*, so never localhost -- use the LAN IP of the laptop / Pi.
    public_host: str = field(default_factory=lambda: _env("VECTOR_PUBLIC_HOST"))
    public_scheme: str = field(default_factory=lambda: _env("VECTOR_PUBLIC_SCHEME", "ws"))
    auth_token: str = field(default_factory=lambda: _env("VECTOR_AUTH_TOKEN"))
    log_level: str = field(default_factory=lambda: _env("VECTOR_LOG_LEVEL", "INFO"))
    # Minutes east of UTC, sent to the device so its clock is right.
    # 330 = IST. The firmware multiplies this by 60 * 1000 itself.
    timezone_offset_minutes: int = field(
        default_factory=lambda: _env_int("VECTOR_TZ_OFFSET_MINUTES", 330)
    )

    # --- audio ----------------------------------------------------------
    # The device always uploads 16 kHz mono Opus (hardcoded in the firmware's
    # hello message). Downlink rate is whatever we declare in our hello.
    uplink_sample_rate: int = 16000
    downlink_sample_rate: int = field(
        default_factory=lambda: _env_int("VECTOR_DOWNLINK_SAMPLE_RATE", 24000)
    )
    frame_duration_ms: int = field(default_factory=lambda: _env_int("VECTOR_FRAME_MS", 60))
    # How many frames to send before pacing to realtime. The firmware's decode
    # queue holds 2400/frame_duration packets (40 at 60 ms) and silently drops
    # the overflow, so we must not outrun it.
    playback_burst_frames: int = field(
        default_factory=lambda: _env_int("VECTOR_PLAYBACK_BURST_FRAMES", 15)
    )

    # --- STT (Deepgram) -------------------------------------------------
    deepgram_api_key: str = field(default_factory=lambda: _env("DEEPGRAM_API_KEY"))
    deepgram_model: str = field(default_factory=lambda: _env("DEEPGRAM_MODEL", "nova-3"))
    deepgram_language: str = field(default_factory=lambda: _env("DEEPGRAM_LANGUAGE", "multi"))
    # Silence (ms) after speech before Deepgram finalises. Lower = snappier
    # turn-taking, higher = fewer mid-sentence cut-offs.
    deepgram_endpointing_ms: int = field(
        default_factory=lambda: _env_int("DEEPGRAM_ENDPOINTING_MS", 400)
    )
    deepgram_utterance_end_ms: int = field(
        default_factory=lambda: _env_int("DEEPGRAM_UTTERANCE_END_MS", 1000)
    )

    # --- LLM (Gemini) ---------------------------------------------------
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    # Model availability varies per key and Google retires models on short
    # notice, so run tools/list_models.py rather than trusting this default.
    # Verified working July 2026: ~1.1 s to first sentence.
    gemini_model: str = field(
        default_factory=lambda: _env("GEMINI_MODEL", "gemini-3.5-flash-lite")
    )
    gemini_api_base: str = field(
        default_factory=lambda: _env(
            "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
        )
    )
    gemini_temperature: float = field(
        default_factory=lambda: float(_env("GEMINI_TEMPERATURE", "0.7"))
    )
    gemini_max_output_tokens: int = field(
        default_factory=lambda: _env_int("GEMINI_MAX_OUTPUT_TOKENS", 512)
    )
    system_prompt: str = field(
        default_factory=lambda: _env(
            "VECTOR_SYSTEM_PROMPT",
            "You are VECTOR, a friendly voice assistant living in a small desk robot. "
            "You are speaking out loud, so keep replies to one or two short sentences. "
            "Never use markdown, bullet points, emoji or special characters -- your "
            "words go straight to a text-to-speech engine. If you do not know "
            "something, say so briefly.",
        )
    )
    history_turns: int = field(default_factory=lambda: _env_int("VECTOR_HISTORY_TURNS", 12))

    # --- TTS ------------------------------------------------------------
    # edge | gemini | piper
    tts_provider: str = field(default_factory=lambda: _env("TTS_PROVIDER", "edge"))
    edge_tts_voice: str = field(
        default_factory=lambda: _env("EDGE_TTS_VOICE", "en-IN-NeerjaNeural")
    )
    edge_tts_rate: str = field(default_factory=lambda: _env("EDGE_TTS_RATE", "+0%"))
    edge_tts_pitch: str = field(default_factory=lambda: _env("EDGE_TTS_PITCH", "+0Hz"))
    # Measured July 2026: this is the fastest Gemini TTS model, and it still
    # takes ~1.9 s for a one-word reply and ~3.1 s for a short sentence. That is
    # a floor, not a warm-up. Fine for pre-generated audio, too slow to
    # converse with -- see tts.py.
    gemini_tts_model: str = field(
        default_factory=lambda: _env("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    )
    gemini_tts_voice: str = field(default_factory=lambda: _env("GEMINI_TTS_VOICE", "Kore"))
    piper_binary: str = field(default_factory=lambda: _env("PIPER_BINARY", "piper"))
    piper_model: str = field(default_factory=lambda: _env("PIPER_MODEL"))
    piper_sample_rate: int = field(default_factory=lambda: _env_int("PIPER_SAMPLE_RATE", 22050))

    ffmpeg_binary: str = field(default_factory=lambda: _env("FFMPEG_BINARY", "ffmpeg"))
    # Emit a "listen"-mode greeting on the first connection of a session.
    greeting: str = field(default_factory=lambda: _env("VECTOR_GREETING"))
    debug_dump_dir: str = field(default_factory=lambda: _env("VECTOR_DEBUG_DUMP_DIR"))

    @property
    def uplink_frame_samples(self) -> int:
        return self.uplink_sample_rate // 1000 * self.frame_duration_ms

    @property
    def downlink_frame_samples(self) -> int:
        return self.downlink_sample_rate // 1000 * self.frame_duration_ms

    def websocket_url(self, request_host: str) -> str:
        """URL handed to the device in the OTA response."""
        host = self.public_host or request_host
        return f"{self.public_scheme}://{host}/xiaozhi/v1/"

    def validate(self) -> list[str]:
        problems = []
        if not self.deepgram_api_key:
            problems.append("DEEPGRAM_API_KEY is not set -- speech recognition will fail.")
        if not self.gemini_api_key:
            problems.append("GEMINI_API_KEY is not set -- the LLM will fail.")
        if self.tts_provider == "gemini" and not self.gemini_api_key:
            problems.append("TTS_PROVIDER=gemini requires GEMINI_API_KEY.")
        if self.tts_provider == "piper" and not self.piper_model:
            problems.append("TTS_PROVIDER=piper requires PIPER_MODEL (path to a .onnx voice).")
        if self.frame_duration_ms not in (20, 40, 60):
            problems.append(
                f"VECTOR_FRAME_MS={self.frame_duration_ms} is unusual; the firmware "
                "defaults to 60."
            )
        return problems


config = Config()
