"""FastAPI app: the OTA/config endpoint plus the device WebSocket.

Two endpoints are all the firmware needs:

  POST /xiaozhi/ota/   -> tells the device where the WebSocket lives
  WS   /xiaozhi/v1/    -> the conversation itself

The OTA endpoint is not optional. The firmware has no compile-time setting for
the WebSocket URL: Ota::CheckVersion() stores whatever arrives in the response's
`websocket` object into NVS, and WebsocketProtocol::OpenAudioChannel() reads it
back from there. Point CONFIG_OTA_URL at this server and the device finds us.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .config import config
from .session import Session

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    for problem in config.validate():
        log.warning("config: %s", problem)
    log.info(
        "listening on %s:%s | stt=deepgram/%s llm=%s tts=%s",
        config.host,
        config.port,
        config.deepgram_model,
        config.gemini_model,
        config.tts_provider,
    )
    yield


app = FastAPI(title="VECTOR Voice Server", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "llm": config.gemini_model, "tts": config.tts_provider}


@app.api_route("/xiaozhi/ota/", methods=["GET", "POST"])
@app.api_route("/xiaozhi/ota", methods=["GET", "POST"])
async def ota(request: Request) -> JSONResponse:
    """Device bootstrap.

    Two things matter here:

    1. Emit ONLY a `websocket` block. Application::InitializeProtocol() prefers
       MQTT whenever an `mqtt` object is present, so including one would send
       the device somewhere else entirely.
    2. Emit `firmware.version` but NOT `firmware.url`. Ota only sets
       has_new_version_ when both are strings, so omitting the URL guarantees
       the device never tries to flash itself from us.
    """
    device_id = request.headers.get("Device-Id", "")
    reported_version = "1.0.0"

    try:
        body = await request.json()
        reported_version = body.get("application", {}).get("version") or reported_version
    except Exception:
        body = {}

    host = config.public_host or request.headers.get("host", "").split(":")[0]
    if config.public_host:
        ws_url = config.websocket_url(config.public_host)
    else:
        ws_url = config.websocket_url(request.headers.get("host", f"{host}:{config.port}"))

    websocket_block: dict = {"url": ws_url, "version": 1}
    if config.auth_token:
        websocket_block["token"] = config.auth_token

    log.info(
        "ota check: device=%s version=%s chip=%s -> %s",
        device_id or "?",
        reported_version,
        body.get("chip_model_name", "?"),
        ws_url,
    )

    return JSONResponse(
        {
            "server_time": {
                "timestamp": int(time.time() * 1000),
                # Minutes: Ota::CheckVersion multiplies this by 60 * 1000.
                # 330 = IST (UTC+5:30).
                "timezone_offset": config.timezone_offset_minutes,
            },
            "firmware": {"version": reported_version},
            "websocket": websocket_block,
        }
    )


@app.websocket("/xiaozhi/v1/")
@app.websocket("/xiaozhi/v1")
async def device_socket(websocket: WebSocket) -> None:
    device_id = websocket.headers.get("device-id", "")

    if config.auth_token:
        supplied = websocket.headers.get("authorization", "")
        expected = config.auth_token
        if not supplied.endswith(expected):
            log.warning("rejecting %s: bad Authorization header", device_id or "?")
            await websocket.close(code=1008)
            return

    await websocket.accept()
    log.info("device connected: %s", device_id or "?")

    session = Session(_FastAPITransport(websocket), config, device_id=device_id)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if (data := message.get("bytes")) is not None:
                await session.handle_audio(data)
            elif (text := message.get("text")) is not None:
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    log.warning("non-JSON text frame: %r", text[:120])
                    continue
                await session.handle_json(payload)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("session crashed")
    finally:
        await session.close()
        log.info("device disconnected: %s", device_id or "?")


class _FastAPITransport:
    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def send_json(self, payload: dict) -> None:
        await self._ws.send_text(json.dumps(payload, ensure_ascii=False))

    async def send_bytes(self, payload: bytes) -> None:
        await self._ws.send_bytes(payload)
