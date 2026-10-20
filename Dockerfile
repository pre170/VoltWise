FROM node:24.16.0-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

FROM python:3.12.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8080 \
    VOLTWISE_DB_PATH=/data/voltwise.db \
    VOLTWISE_STATIC_DIR=/app/frontend/dist

WORKDIR /app
COPY requirements-deploy.lock ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements-deploy.lock \
    && groupadd --system voltwise \
    && useradd --system --gid voltwise --home-dir /app --shell /usr/sbin/nologin voltwise \
    && mkdir -p /data /app/frontend \
    && chown -R voltwise:voltwise /data /app

COPY --chown=voltwise:voltwise backend/app ./backend/app
COPY --chown=voltwise:voltwise --from=frontend-build /build/frontend/dist ./frontend/dist
COPY --chown=voltwise:voltwise LICENSE README.md ./

USER voltwise
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8080') + '/health', timeout=2).read()"

CMD ["python", "-m", "app.deployment"]
