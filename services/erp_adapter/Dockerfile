# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for the erp_adapter service (Vol 1 S9.3).
# Build context is the repo root: docker build -f services/erp_adapter/Dockerfile .

FROM python:3.15-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# crepro-common is not published to PyPI, so it is installed from this monorepo
# alongside the service itself (ADR-014: one package per service, shared code
# under packages/crepro-common).
COPY packages/crepro-common ./packages/crepro-common
COPY services/erp_adapter ./services/erp_adapter

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ./packages/crepro-common ./services/erp_adapter

FROM python:3.15-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /home/app
EXPOSE 8011

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8011/health', timeout=2)" || exit 1

CMD ["uvicorn", "crepro_erp_adapter.main:app", "--host", "0.0.0.0", "--port", "8011"]
