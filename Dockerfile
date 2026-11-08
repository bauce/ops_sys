# syntax=docker/dockerfile:1

# ---------- 前端构建 ----------
FROM node:22-alpine AS web
ARG NPM_REGISTRY=https://registry.npmjs.org
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry "$NPM_REGISTRY" \
    && npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 运行时 ----------
FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    OPS_DB=/app/backend/data/ops.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=web /web/dist /app/frontend/dist

RUN mkdir -p /app/backend/data/uploads

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8008/api/health || exit 1

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
