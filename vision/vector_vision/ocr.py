"""Optical character recognition (skeleton).

Wraps an OCR engine (Tesseract via `pytesseract`, or EasyOCR). Stubbed so the
package stays lightweight; fill in :meth:`read_text` with your engine of choice.
"""

from __future__ import annotations

from typing import Any


class OCR:
    def read_text(self, frame: Any) -> str:  # noqa: ARG002
        """Return recognised text from a frame/region."""
        # TODO: e.g. `return pytesseract.image_to_string(frame)`
        return ""
