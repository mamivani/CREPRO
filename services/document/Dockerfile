# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for the document service (Vol 1 S9.3).
# Build context is the repo root: docker build -f services/document/Dockerfile .

FROM python:3.13-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# crepro-common is not published to PyPI, so it is installed from this monorepo
# alongside the service itself (ADR-014: one package per service, shared code
# under packages/crepro-common).
COPY packages/crepro-common ./packages/crepro-common
COPY services/document ./services/document

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ./packages/crepro-common ./services/document

# DELIBERATE, TEMPORARY: swapped the runtime base to the exact image Aqua's
# own Trivy quickstart docs use as a known-vulnerable demo target, to verify
# Day 4's container-scan merge gate (docs/plan/15-day-plan-solo.md). Skipping
# the normal copy/user setup entirely -- this build only needs to produce an
# image for Trivy to scan, not a working service. This branch/PR will be
# closed without merging once confirmed.
FROM python:3.4-alpine AS runtime
CMD ["true"]
