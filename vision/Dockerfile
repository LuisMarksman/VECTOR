# VECTOR vision worker
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY vector_vision ./vector_vision

# NOTE: the OpenCV/YOLO backends need extra system libraries
# (libgl1, libglib2.0-0) and model weights. The default mock backend does not.

CMD ["python", "-m", "vector_vision"]
