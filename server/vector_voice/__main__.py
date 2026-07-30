"""Run with: python -m vector_voice"""

from __future__ import annotations

import os

import uvicorn

try:
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("VECTOR_ENV_FILE", ".env"))
except ImportError:  # pragma: no cover
    pass


def main() -> None:
    # Imported after load_dotenv so the config dataclass sees the .env values.
    from .config import config

    uvicorn.run(
        "vector_voice.app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
