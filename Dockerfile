# cloak-fallback sidecar: stealth-Chromium HTTP fetcher behind aiohttp.
#
# Build: docker build -t cloak-fallback:latest .
# Image size is ~900 MB (Python base + Playwright + Chromium 145 + system libs).

FROM python:3.12-slim AS base

# Minimal runtime libs Chromium needs in slim base.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libwayland-client0 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxkbcommon0 \
        libxrandr2 \
        libxrender1 \
        libxshmfence1 \
        libxss1 \
        libxtst6 \
        xdg-utils \
        wget \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download Chromium so first request doesn't pay the ~140 MB download cost.
# Binary lands at /root/.cloakbrowser/chromium-<version>/.
RUN cloakbrowser install

COPY server.py .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health > /dev/null || exit 1

CMD ["python", "server.py"]
