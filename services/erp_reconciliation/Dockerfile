# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for the ERP reconciliation job.
# Build context is the repo root: docker build -f services/erp_reconciliation/Dockerfile .

FROM python:3.13-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# crepro-common and crepro-erp-adapter aren't published to PyPI, so they're
# installed from this monorepo alongside the job itself (ADR-014). Reconciliation's
# real-client path lazily imports ERPClient/PostgresLedgerRepo/DaprDLQRepo/
# AdapterServiceClient from crepro_erp_adapter (see main.py _initialize_clients).
COPY packages/crepro-common ./packages/crepro-common
COPY services/erp_adapter ./services/erp_adapter
COPY services/erp_reconciliation ./services/erp_reconciliation

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ./packages/crepro-common ./services/erp_adapter ./services/erp_reconciliation

FROM python:3.13-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /home/app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the reconciliation job (RECONCILIATION_MODE/TENANT_ID etc. via environment,
# see main.py); Azure Container Apps Jobs invoke this once per scheduled trigger.
ENTRYPOINT ["python", "-m", "crepro_erp_reconciliation.main"]
