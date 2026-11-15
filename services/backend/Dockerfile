# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for the consolidated backend. It serves the
# tenant, property, lease, reservation, payment, document, utility,
# maintenance, and reporting routers from one process on port 8003.
# Build context is the repo root: docker build -f services/backend/Dockerfile .

FROM python:3.13-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# crepro-common and the domain packages are not published to PyPI, so they are
# installed from this monorepo (ADR-014: one package per service, shared code
# under packages/crepro-common).
COPY packages/crepro-common ./packages/crepro-common
COPY services/backend ./services/backend
COPY services/tenant ./services/tenant
COPY services/property ./services/property
COPY services/lease ./services/lease
COPY services/reservation ./services/reservation
COPY services/payment ./services/payment
COPY services/document ./services/document
COPY services/utility ./services/utility
COPY services/maintenance ./services/maintenance
COPY services/reporting ./services/reporting

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      ./packages/crepro-common \
      ./services/tenant \
      ./services/property \
      ./services/lease \
      ./services/reservation \
      ./services/payment \
      ./services/document \
      ./services/utility \
      ./services/maintenance \
      ./services/reporting \
      ./services/backend

FROM python:3.13-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /home/app
EXPOSE 8003

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)" || exit 1

CMD ["uvicorn", "crepro_backend.main:app", "--host", "0.0.0.0", "--port", "8003"]
