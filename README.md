# cloak-fallback

Stealth-Chromium HTTP sidecar. Drop-in fallback for [`social-ingest`](https://github.com/alik280290-lang/social-ingest) when its primary path hits anti-bot defenses (Cloudflare, Datadome, FingerprintJS, etc.).

Built on [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) — a Chromium fork with 49 C++ source-level fingerprint patches.

## API

`GET /health` →

```json
{"ok": true, "chromium_ready": true, "cloakbrowser_version": "0.3.28", "max_concurrent": 1, "in_flight": 0}
```

`POST /fetch` body:

```json
{
  "url": "https://example.com",
  "humanize": true,
  "wait": 3,
  "timeout": 45000,
  "screenshot": "/tmp/shot.png",
  "text_only": false,
  "user_agent": null,
  "proxy": "http://user:pass@host:port",
  "no_headless": false
}
```

→ JSON envelope:

```json
{
  "ok": true,
  "url": "...",
  "final_url": "...",
  "status": 200,
  "title": "...",
  "text": "...",
  "html_bytes": 12345,
  "screenshot_path": "...",
  "elapsed_ms": 6295,
  "tool": "cloakbrowser"
}
```

Errors return `502` with the same shape but `ok:false` and `error: {code, message}`.

## Deploy on VPS (OpenClaw compose)

In `/docker/openclaw-d60p/docker-compose.yml`:

```yaml
services:
  cloak-fallback:
    build:
      context: /docker/cloak-fallback
    container_name: cloak-fallback
    restart: unless-stopped
    networks:
      - default
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1500M
```

Then on the VPS:

```bash
git clone https://github.com/alik280290-lang/cloak-fallback.git /docker/cloak-fallback
cd /docker/openclaw-d60p
docker compose up -d cloak-fallback
docker compose exec openclaw curl -fsS http://cloak-fallback:8080/health
```

## Resource notes

- Image ~900 MB (Python + Chromium 145 + system libs)
- ~500 MB RAM per active fetch (Python ~263 MB + Chromium children)
- ~6 sec cold-start request, ~2 sec warm
- `CLOAK_MAX_CONCURRENT=1` by default (8 GB / 2-core VPS — safe ceiling)

## Agents config

Each agent reads `CLOAK_URL=http://cloak-fallback:8080/fetch` from its env.
Fallback is invoked ONLY when the primary fetcher fails — see each agent's `SOUL.md`.
