# syntax=docker/dockerfile:1
# OCI-compliant, multi-stage image for crepro-common (Vol 1 S9.3).
# crepro-common is a library, not a service: this image exists so build.yml can
# build and test it in the same image-matrix pattern as every service, and so
# the installed package can be inspected/reused as a base layer if needed.
# Build context is the repo root: docker build -f packages/crepro-common/Dockerfile .

FROM python:3.15-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY packages/crepro-common ./packages/crepro-common

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir "./packages/crepro-common[dev]"

# Tests run as a build step: a broken shared library fails the image build
# itself, before any service gets a chance to depend on it.
RUN pytest packages/crepro-common/tests

FROM python:3.15-slim AS runtime

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /home/app

CMD ["python", "-c", "import crepro_common; print('crepro_common import OK')"]
