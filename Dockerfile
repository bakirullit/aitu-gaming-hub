# ==========================================
# Stage 1: Build Vue 3 Frontend SPA
# ==========================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY web/app/package*.json ./
RUN npm ci

COPY web/app/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Application Runtime
# ==========================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal OS dependencies for Postgres client & healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY common/ ./common/
COPY core/ ./core/
COPY plugins/ ./plugins/
COPY services/ ./services/
COPY web/ ./web/
COPY main.py .

# Copy prebuilt Vue SPA artifacts from Stage 1 into web/app/dist
COPY --from=frontend-builder /app/frontend/dist ./web/app/dist

# Expose FastAPI & Ingress port
EXPOSE 8000

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Entrypoint runs migrations and launches the application
CMD ["sh", "-c", "alembic upgrade head && python main.py"]
