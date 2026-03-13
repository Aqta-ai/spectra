"""Screen capture tools for Spectra agents."""

import base64
import io
from typing import Any

import mss
from PIL import Image


def capture_screenshot() -> dict[str, Any]:
    """Capture the current screen and return as base64 JPEG.

    Returns a dict with mime_type and base64-encoded image data,
    ready to send to Gemini vision.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[0]  # Full screen
        raw = sct.grab(monitor)

    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    img.thumbnail((1280, 1280), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)

    return {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(buf.read()).decode(),
    }
