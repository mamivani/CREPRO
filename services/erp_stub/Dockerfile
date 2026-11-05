# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for the ERP stub service.
# Build context is the repo root: docker build -f services/erp_stub/Dockerfile .

FROM python:3.13-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY services/erp_stub ./services/erp_stub

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ./services/erp_stub

FROM python:3.13-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /home/app
EXPOSE 8100

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/api/health', timeout=2)" || exit 1

CMD ["uvicorn", "crepro_erp_stub.main:app", "--host", "0.0.0.0", "--port", "8100"]
