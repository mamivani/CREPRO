# Multi-stage build for ERP Reconciliation Service

# Stage 1: Build
FROM python:3.13-slim as builder

WORKDIR /build

# Copy common package
COPY packages/crepro-common /build/packages/crepro-common

# Copy reconciliation service
COPY services/erp_reconciliation /build/services/erp_reconciliation

# Install dependencies
RUN cd /build/packages/crepro-common && pip install -e .
RUN cd /build/services/erp_reconciliation && pip install -e .

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY services/erp_reconciliation/src /app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Run the reconciliation job
ENTRYPOINT ["python", "-m", "crepro_erp_reconciliation.main"]
