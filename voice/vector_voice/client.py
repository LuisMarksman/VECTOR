"""HTTP client for the VECTOR server."""

from __future__ import annotations

import httpx


class VectorClient:
    def __init__(self, base_url: str, session_id: str = "voice", timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._session_id = session_id
        self._http = httpx.Client(timeout=timeout)

    def send(self, text: str) -> str:
        """Send a command to the server and return the assistant's reply text."""
        resp = self._http.post(
            f"{self._base_url}/assistant/command",
            json={"text": text, "session_id": self._session_id},
        )
        resp.raise_for_status()
        return resp.json()["text"]

    def close(self) -> None:
        self._http.close()
