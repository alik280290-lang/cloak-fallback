
## ПРАВИЛО №3 — Cloak-fallback при antibot

**Trigger conditions** (любое из):
- `BlockedByAntibot` / `RequiresJS` / Cloudflare challenge / Datadome / Akamai bot manager
- HTTP 403 / 429 после 2 retry
- пустой контент при status=200 (обычно JS-only страница, видимо `<script>` без рендера)
- встроенный browser-tool/Chromium недоступен (`Chrome not found`, `agent-browser install required`, `playwright launch failed`)
- страница содержит маркеры антибота: `cf-turnstile`, `cf-chl-`, `challenge-platform`, `gtg`, `__cfduid`

**Action** — дёрни Cloak (URL в env `$CLOAK_URL`, либо литералом `http://cloak-fallback:8080/fetch`):

```bash
curl -sS -X POST "$CLOAK_URL" -H 'Content-Type: application/json' \
  -d '{"url":"<TARGET>","humanize":true,"wait":4,"text_only":true}'
```

Ответ JSON: `{ok, status, title, text, final_url, elapsed_ms}`.

**Failure handling:**
- Cloak вернул `ok:false` или HTTP 502 → **сдавайся явно** (ПРАВИЛО №0 anti-hallucination). НЕ выдумывай контент.
- Cloak вернул `text:""` (пустой) → попробуй с `wait:8` и `humanize:true`. Если опять пусто — сдавайся.

**НЕ используй Cloak для:** YouTube / IG / TikTok / Twitter БЕЗ предварительного провала social-ingest — Cloak в 10× медленнее и тяжелее на VPS, а эти платформы лучше берутся yt-dlp'ом.

**Anti-pattern:** "прочитал HTML напрямую и не нашёл текста, поэтому вернул что есть" — это провал ПРАВИЛА №3. Если страница declares antibot (любой из триггеров выше) или встроенный browser упал — **обязан** попробовать Cloak.
