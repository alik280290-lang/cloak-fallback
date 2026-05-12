"""
cloak-fallback HTTP sidecar.

Wraps CloakBrowser stealth Chromium behind a tiny HTTP API that returns the
same JSON envelope shape as social-ingest. Designed to be called by agents
when their primary fetcher (yt-dlp / social-ingest) hits anti-bot, 403, or
RequiresJS errors.

Endpoints:
  GET  /health      → {"ok": true, "chromium_ready": bool, "version": str}
  POST /fetch       → JSON body {url, humanize?, wait?, timeout?, screenshot?,
                                  text_only?, user_agent?, proxy?, no_headless?}
                       → JSON envelope (see fetch_one below)

Concurrency: one browser per request (cold-start ~2s + page wait).
We serialize requests via an asyncio.Semaphore(MAX_CONCURRENT) to avoid OOM on
2-core / 8GB VPS where each browser is ~500 MB.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from aiohttp import web

log = logging.getLogger("cloak-fallback")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

MAX_CONCURRENT = int(os.environ.get("CLOAK_MAX_CONCURRENT", "1"))
DEFAULT_TIMEOUT_MS = int(os.environ.get("CLOAK_DEFAULT_TIMEOUT_MS", "45000"))
DEFAULT_WAIT_SEC = float(os.environ.get("CLOAK_DEFAULT_WAIT_SEC", "3"))
PORT = int(os.environ.get("PORT", "8080"))

SEM = asyncio.Semaphore(MAX_CONCURRENT)


def _chromium_info() -> dict:
    try:
        from cloakbrowser.binary import get_binary_path  # type: ignore
        path = get_binary_path()
        return {"path": str(path) if path else None, "ready": path is not None and Path(path).exists()}
    except Exception:
        cb_dir = Path.home() / ".cloakbrowser"
        if cb_dir.exists():
            candidates = list(cb_dir.glob("chromium-*"))
            if candidates:
                return {"path": str(candidates[0]), "ready": True}
        return {"path": None, "ready": False}


async def health(_request: web.Request) -> web.Response:
    info = _chromium_info()
    try:
        import cloakbrowser  # type: ignore
        version = getattr(cloakbrowser, "__version__", "unknown")
    except Exception:
        version = None
    return web.json_response({
        "ok": True,
        "chromium_ready": info["ready"],
        "chromium_path": info["path"],
        "cloakbrowser_version": version,
        "max_concurrent": MAX_CONCURRENT,
        "in_flight": MAX_CONCURRENT - SEM._value,
    })


def fetch_one(
    url: str,
    humanize: bool,
    wait_sec: float,
    timeout_ms: int,
    screenshot_path: str | None,
    text_only: bool,
    user_agent: str | None,
    proxy: str | None,
    headless: bool,
) -> dict:
    started = time.time()
    out: dict = {"ok": False, "url": url, "tool": "cloakbrowser"}

    try:
        from cloakbrowser import launch  # type: ignore
    except Exception as e:
        out["error"] = {"code": "ImportError", "message": str(e)}
        out["elapsed_ms"] = int((time.time() - started) * 1000)
        return out

    launch_kwargs: dict = {"headless": headless, "humanize": humanize}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}

    browser = None
    try:
        browser = launch(**launch_kwargs)

        if user_agent:
            ctx = browser.new_context(user_agent=user_agent)
            page = ctx.new_page()
        else:
            page = browser.new_page()

        resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if wait_sec > 0:
            page.wait_for_timeout(int(wait_sec * 1000))

        out["final_url"] = page.url
        out["status"] = resp.status if resp else None
        out["title"] = page.title()

        try:
            text = page.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception:
            text = ""
        out["text"] = text or ""

        if not text_only:
            try:
                html = page.content()
                out["html_bytes"] = len(html.encode("utf-8"))
            except Exception:
                out["html_bytes"] = 0

        if screenshot_path:
            shot = Path(screenshot_path)
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True)
            out["screenshot_path"] = str(shot)

        out["ok"] = True
        out["elapsed_ms"] = int((time.time() - started) * 1000)
        return out

    except Exception as e:
        out["error"] = {"code": type(e).__name__, "message": str(e)[:500]}
        out["elapsed_ms"] = int((time.time() - started) * 1000)
        return out
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


async def fetch_endpoint(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": {"code": "BadRequest", "message": "invalid JSON"}}, status=400)

    url = body.get("url")
    if not url or not isinstance(url, str):
        return web.json_response({"ok": False, "error": {"code": "BadRequest", "message": "url required"}}, status=400)

    params = dict(
        humanize=bool(body.get("humanize", False)),
        wait_sec=float(body.get("wait", DEFAULT_WAIT_SEC)),
        timeout_ms=int(body.get("timeout", DEFAULT_TIMEOUT_MS)),
        screenshot_path=body.get("screenshot"),
        text_only=bool(body.get("text_only", False)),
        user_agent=body.get("user_agent"),
        proxy=body.get("proxy"),
        headless=not bool(body.get("no_headless", False)),
    )

    log.info("fetch url=%s humanize=%s wait=%s timeout=%s",
             url, params["humanize"], params["wait_sec"], params["timeout_ms"])

    async with SEM:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: fetch_one(url, **params))

    status = 200 if result.get("ok") else 502
    return web.json_response(result, status=status)


def build_app() -> web.Application:
    app = web.Application(client_max_size=1024 * 1024)
    app.router.add_get("/health", health)
    app.router.add_post("/fetch", fetch_endpoint)
    return app


def main() -> None:
    app = build_app()
    log.info("cloak-fallback listening on :%d (max_concurrent=%d)", PORT, MAX_CONCURRENT)
    web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)


if __name__ == "__main__":
    main()
