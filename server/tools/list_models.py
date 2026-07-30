#!/usr/bin/env python3
"""Ask your Gemini key which models it can actually reach.

Google retires models faster than docs update -- gemini-2.5-flash started
returning 404 in July 2026, ahead of its announced October shutdown. Run this
before setting GEMINI_MODEL rather than trusting any blog post (including the
default in config.py).

    python tools/list_models.py
"""

from __future__ import annotations

import os
import sys

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("VECTOR_ENV_FILE", ".env"))
except ImportError:
    pass

API_BASE = os.environ.get(
    "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
)


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY is not set", file=sys.stderr)
        return 1

    models: list[dict] = []
    page_token = None
    with httpx.Client(timeout=30.0) as client:
        while True:
            params = {"pageSize": 200}
            if page_token:
                params["pageToken"] = page_token
            response = client.get(
                f"{API_BASE}/models", headers={"x-goog-api-key": key}, params=params
            )
            if response.status_code != 200:
                print(f"{response.status_code}: {response.text[:400]}", file=sys.stderr)
                return 1
            data = response.json()
            models.extend(data.get("models", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    generate, speech, other = [], [], []
    for model in models:
        name = model.get("name", "").removeprefix("models/")
        methods = model.get("supportedGenerationMethods", [])
        if "tts" in name or "speech" in name:
            speech.append((name, methods))
        elif "generateContent" in methods:
            generate.append((name, methods))
        else:
            other.append((name, methods))

    print(f"=== text / multimodal ({len(generate)}) -- pick one for GEMINI_MODEL ===")
    for name, _ in sorted(generate):
        print(f"  {name}")

    print(f"\n=== speech ({len(speech)}) -- pick one for GEMINI_TTS_MODEL ===")
    for name, methods in sorted(speech):
        print(f"  {name}  [{', '.join(methods)}]")

    if other:
        print(f"\n=== other ({len(other)}) ===")
        for name, methods in sorted(other):
            print(f"  {name}  [{', '.join(methods)}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
