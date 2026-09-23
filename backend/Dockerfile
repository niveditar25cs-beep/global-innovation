# =============================================================================
# Multi-stage Dockerfile for Transformer Failure Risk Monitoring Backend
#
# Stage 1: builder  — Install Python dependencies into an isolated venv
# Stage 2: runtime  — Copy venv + app source; run as non-root user
# =============================================================================

# ─────────────────────────── Stage 1: builder ────────────────────────────────
FROM python:3.11-slim AS builder

LABEL stage="builder"

# Build-time dependencies (compilers, libpq headers for psycopg2)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ─── Install Python dependencies (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
    && pip install --no-cache-dir -r requirements.txt


# ─────────────────────────── Stage 2: runtime ────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Global Innovation Backend"
LABEL org.opencontainers.image.title="Transformer Risk Monitoring Backend"
LABEL org.opencontainers.image.description="FastAPI backend for Transformer Failure Risk Monitoring"

# Runtime dependencies only (no build tools; curl for HEALTHCHECK)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Import the pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ─── Create a dedicated non-root system user and group
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

# ─── Set working directory; create necessary subdirectories with correct ownership
WORKDIR /app

# Copy application source code (owned by appuser)
COPY --chown=appuser:appgroup . .

# Ensure the data directory is writable for sample dataset access
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

# ─── Drop root privileges — all subsequent commands run as appuser
USER appuser

# Expose the application port
EXPOSE 8000

# ─── Container health check (tests the /api/v1/health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# ─── Default entrypoint: run Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--access-log"]
