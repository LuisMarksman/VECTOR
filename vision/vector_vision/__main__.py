"""Entrypoint: ``python -m vector_vision``."""

from __future__ import annotations

import logging

from vector_vision.worker import VisionWorker


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    VisionWorker().run()


if __name__ == "__main__":
    main()
