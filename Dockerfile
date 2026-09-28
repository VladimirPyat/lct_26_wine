# Vine Scanner app image (GPU). CUDA 13 / cuDNN 9 come as pip wheels (onnxruntime-gpu[cuda,cudnn]);
# the host needs only the NVIDIA driver (>= 580) + NVIDIA Container Toolkit.
# Models (bin/), catalog data (data/) and catalog images (static/wines/) are mounted, not copied.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_NO_SYNC=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    LD_LIBRARY_PATH=/app/.venv/lib/python3.12/site-packages/nvidia/cu13/lib:/app/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib

# OpenCV (pulled by PHOCR) needs libGL / glib at import time
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock requirements-gpu.txt ./
RUN uv sync --frozen --extra ml --extra db \
    && uv pip uninstall onnxruntime \
    && uv pip install -r requirements-gpu.txt

COPY alembic.ini ./
COPY alembic/ alembic/
COPY config/ config/
COPY src/ src/
COPY scripts/ scripts/
RUN mkdir -p bin data static/wines

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=300s --retries=6 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080"]
