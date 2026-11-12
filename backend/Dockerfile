# Backend image for the compose stack.
#
# Dependencies are read from pyproject.toml rather than a second requirements
# file, so the image can never drift from the declared dependency set.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

# libgl1/libglib2.0-0 are needed by the OpenCV build used for page images;
# poppler is not required because PDF text comes from PyMuPDF.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/pyproject.toml ./pyproject.toml

# CPU-only torch first. sentence-transformers pulls torch as a dependency, and
# its default wheel drags in ~2 GB of CUDA libraries this container can never
# use; installing the CPU build up front keeps the image deployable on a plain
# application server and makes the download survive a slow connection.
RUN python -m pip install --no-cache-dir --retries 10 --timeout 180 \
        --index-url https://download.pytorch.org/whl/cpu torch

RUN python -c "import subprocess, sys, tomllib; deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--retries', '10', '--timeout', '180', *deps])"

COPY backend/ ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
