"""Message builders for the xiaozhi-esp32 WebSocket protocol.

Reference: xiaozhi-esp32/docs/websocket.md and main/protocols/websocket_protocol.cc.
Only the server -> device direction needs constructing; the other direction is
parsed inline in session.py.
"""

from __future__ import annotations

from typing import Any


def server_hello(session_id: str, sample_rate: int, frame_duration_ms: int) -> dict[str, Any]:
    """Handshake reply. The firmware requires transport == "websocket" and uses
    audio_params to reconfigure its Opus decoder (AudioService::SetDecodeSampleRate)."""
    return {
        "type": "hello",
        "transport": "websocket",
        "session_id": session_id,
        "audio_params": {
            "format": "opus",
            "sample_rate": sample_rate,
            "channels": 1,
            "frame_duration": frame_duration_ms,
        },
    }


def stt(session_id: str, text: str) -> dict[str, Any]:
    """Recognised user speech -- the firmware prints this on the display."""
    return {"session_id": session_id, "type": "stt", "text": text}


def llm_emotion(session_id: str, emotion: str, text: str = "") -> dict[str, Any]:
    """Drives the on-device face/emoji."""
    return {"session_id": session_id, "type": "llm", "emotion": emotion, "text": text}


def tts_start(session_id: str) -> dict[str, Any]:
    """Moves the device into the speaking state; it stops uploading mic audio."""
    return {"session_id": session_id, "type": "tts", "state": "start"}


def tts_sentence_start(session_id: str, text: str) -> dict[str, Any]:
    """Subtitle for the sentence about to be spoken."""
    return {"session_id": session_id, "type": "tts", "state": "sentence_start", "text": text}


def tts_stop(session_id: str) -> dict[str, Any]:
    """Ends the turn. In auto mode the device goes straight back to listening."""
    return {"session_id": session_id, "type": "tts", "state": "stop"}


def alert(session_id: str, status: str, message: str, emotion: str = "sad") -> dict[str, Any]:
    return {
        "session_id": session_id,
        "type": "alert",
        "status": status,
        "message": message,
        "emotion": emotion,
    }


def mcp(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """JSON-RPC 2.0 envelope for device tool calls."""
    return {"session_id": session_id, "type": "mcp", "payload": payload}


# Emotions the firmware's display layer understands. Anything else falls back
# to neutral, so we clamp before sending.
KNOWN_EMOTIONS = {
    "neutral", "happy", "laughing", "funny", "sad", "angry", "crying",
    "loving", "embarrassed", "surprised", "shocked", "thinking", "winking",
    "cool", "relaxed", "delicious", "kissy", "confident", "sleepy", "silly",
    "confused",
}


def clamp_emotion(emotion: str) -> str:
    emotion = (emotion or "").strip().lower()
    return emotion if emotion in KNOWN_EMOTIONS else "neutral"
