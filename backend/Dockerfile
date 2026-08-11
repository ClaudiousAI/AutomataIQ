# SAIE backend — production image (M01).
#
# Three-stage build:
#   builder     — install build deps (none today, but reserved for
#                 later modules that need C extensions).
#   runtime     — slim image with the resolved wheels only.
#   test        — used by CI to run ``make test`` without polluting
#                 the runtime image.
#
# Traceability: NFR-004 (no secrets baked in), NFR-005 (healthcheck
# declared here so ``docker compose up`` gates on liveness),
# NFR-006 (typed image; pinned Python patch version).

ARG PYTHON_VERSION=3.12.3-slim-bookworm

# --- builder ------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# --- runtime ------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Non-root user for least-privilege execution (NFR-004).
RUN groupadd --system --gid 1001 saie \
    && useradd --system --uid 1001 --gid saie saie

COPY --from=builder /install /usr/local
COPY app ./app
COPY notifications ./notifications

USER saie

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
