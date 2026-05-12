
## ПРАВИЛО №3 — Cloak-fallback при antibot

Если URL-ингест (social-ingest / fetch / yt-dlp) вернул:
- `BlockedByAntibot` / `RequiresJS` / Cloudflare challenge
- HTTP 403 после 2 retry
- пустой контент при status=200 (обычно JS-only страница)

→ дёрни Cloak (URL в env `$CLOAK_URL`):

```bash
curl -sS -X POST "$CLOAK_URL" -H 'Content-Type: application/json' \
  -d '{"url":"<TARGET>","humanize":true,"wait":4,"text_only":true}'
```

Ответ JSON: `{ok, status, title, text, final_url, elapsed_ms}`.

Если Cloak вернул `ok:false` или 502 — **сдавайся явно** (ПРАВИЛО №0 anti-hallucination). НЕ выдумывай контент.

Не используй Cloak для YouTube/IG/TikTok/Twitter БЕЗ предварительного провала social-ingest — он в 10× медленнее и тяжелее на VPS.
