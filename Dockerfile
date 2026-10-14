# ==============================================================================
# VendorGuard AI - Unified Production Container
# All-in-One: Next.js UI/UX Frontend, FastAPI Analytical Backend,
#             Durable Worker, and Pre-seeded SQLite Database.
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Next.js Web Frontend
# ------------------------------------------------------------------------------
FROM node:20-slim AS web-builder

WORKDIR /app/apps/web

# Install web build dependencies
COPY apps/web/package*.json ./
RUN npm ci

# Copy web source files
COPY apps/web ./

# Build Next.js production bundle
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Final Unified Container Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim

LABEL maintainer="VendorGuard AI Team"
LABEL description="Unified container running VendorGuard AI UI/UX frontend and analytical backend"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DATABASE_URL="sqlite:////app/vendorguard.db" \
    ASYNC_DATABASE_URL="sqlite+aiosqlite:////app/vendorguard.db" \
    BACKEND_INTERNAL_URL="http://127.0.0.1:8000" \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Install Node.js 20, curl, sqlite3, and process tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    sqlite3 \
    procps \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python backend requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code, versioned policies, synthetic datasets, and replay artifacts
COPY backend ./backend
COPY policies ./policies
COPY datasets ./datasets
COPY research ./research

# Copy built Next.js application from stage 1
COPY --from=web-builder /app/apps/web /app/apps/web

# Copy and setup entrypoint
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Ports:
# 3000: Next.js UI/UX Frontend (primary application portal, proxies /api/* internally)
# 8000: FastAPI Backend (optional direct API access)
EXPOSE 3000
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=25s --retries=3 \
  CMD curl -f http://127.0.0.1:3000/ready || curl -f http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
