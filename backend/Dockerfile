# Backend image for the `api` service in docker-compose.yml.
#
# Built from the repository root (docker-compose.yml sets `build.context: .`),
# so the layout inside the image matches a local checkout:
#
#   /app/backend/...   application package, alembic config, runtime var/ state
#   /app/data/...      golden evaluation dataset (bind-mounted at runtime)
#
# The service command runs `alembic upgrade head` from /app/backend, which is
# also where uvicorn can import `app.main`.

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# libglib2.0-0/libgl1/libgomp1 are required by the OCR stack (PaddleOCR/OpenCV);
# curl backs the healthcheck below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Dependency layer first — use pinned requirements.txt so Docker builds are
# reproducible. Application edits after this point do not reinstall the wheels.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Install the package itself (editable installs don't work in Docker; use a
# regular install from the source tree).
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
RUN python -m pip install --no-deps "/app/backend[ocr]"

# The rest of the backend is code and configuration, not dependencies.
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/alembic /app/backend/alembic

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
