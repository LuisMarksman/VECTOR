# Multi-arch: builds unchanged on the x86-64 laptop and the arm64 Raspberry Pi.
# python:3.11-slim-bookworm has official linux/arm64 images, so
# `docker compose up --build` on the Pi just works.
FROM python:3.11-slim-bookworm

# libopus0  -> opuslib loads this via ctypes at import time
# ffmpeg    -> MP3 decode + resampling in the TTS path
RUN apt-get update && apt-get install -y --no-install-recommends \
        libopus0 \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vector_voice ./vector_voice
COPY tools ./tools

ENV PYTHONUNBUFFERED=1 \
    VECTOR_HOST=0.0.0.0 \
    VECTOR_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://127.0.0.1:8000/health', timeout=3).status_code==200 else 1)"

CMD ["python", "-m", "vector_voice"]
