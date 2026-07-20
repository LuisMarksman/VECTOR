"""Entrypoint: ``python -m vector_voice``."""

from __future__ import annotations

import logging

from vector_voice.assistant import VoiceAssistant


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    VoiceAssistant().run()


if __name__ == "__main__":
    main()
