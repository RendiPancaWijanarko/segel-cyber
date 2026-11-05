# SPDX-License-Identifier: MIT
# SEGEL Docker image for the MVP demonstration lab.
#
# This is a minimal image for running the Release Desk web application
# and receiver/approver/witness CLI tools in Docker containers.

FROM python:3.12-slim

LABEL maintainer="SEGEL Team"
LABEL description="SEGEL - Sistem Edar Gelar Elektronik Lapis-ganda"
LABEL version="0.1.0-mvp"

# Security: run as non-root
RUN groupadd -r segel && useradd -r -g segel -m segel

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER segel

# Default port for Release Desk
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Default command: run the Release Desk
CMD ["uvicorn", "release_desk.app:app", "--host", "0.0.0.0", "--port", "8000"]

