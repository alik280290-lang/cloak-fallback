---
name: reddit
description: "Reddit via public JSON API: subreddit hot/new/top, post comments, search, user profiles. No auth required."
version: 1.0.0
platforms: [linux, macos, windows]
prerequisites:
  commands: [curl, jq]
metadata:
  hermes:
    tags: [reddit, social-media, json-api, research, no-auth]
---

# Reddit research skill

Reddit exposes public JSON for almost everything. Add `.json` to any reddit URL → get structured data. No auth, no API key. Rate-limit ~60 rpm per IP.

## When to use

- Hot/new/top posts in a subreddit
- Full comment tree of a post
- Search across reddit
- User profile/posts/comments
- Watchlist monitoring

## Quick reference

```bash
# Hot posts
curl -sH "User-Agent: hermes-bot/1.0" "https://www.reddit.com/r/Entrepreneur/hot.json?limit=10" \
  | jq '.data.children[] | {title: .data.title, score: .data.score, comments: .data.num_comments, url: .data.url, permalink: .data.permalink}'

# Top this week
curl -sH "User-Agent: hermes-bot/1.0" "https://www.reddit.com/r/marketing/top.json?t=week&limit=10" \
  | jq '.data.children[] | {title: .data.title, score: .data.score, comments: .data.num_comments, ratio: .data.upvote_ratio}'

# Comments tree
curl -sH "User-Agent: hermes-bot/1.0" "https://www.reddit.com/r/Entrepreneur/comments/POST_ID/.json?limit=100&depth=3" \
  | jq '[.[1].data.children[].data | {author, body, score}]'

# Search
curl -sH "User-Agent: hermes-bot/1.0" "https://www.reddit.com/search.json?q=QUERY&sort=relevance&t=week&limit=25" \
  | jq '.data.children[].data | {subreddit, title, score, num_comments, permalink}'
```

## Helper script

`SKILL_DIR/scripts/reddit_hot.sh r/SUB LIMIT` — печатает топ постов: score | comments | title | URL.

## Tricks for watchlist

- `?t=hour|day|week|month|year|all` для `/top/`
- `/r/SUB/about.json` → subscribers count, описание
- `/r/all/hot.json?limit=100` → reddit-wide тренды
- `User-Agent` **обязателен** — без него reddit банит на ~60 сек
- `?after=t3_POSTID` для пагинации

## Anti-pattern

НЕ парси HTML reddit.com через browser/cloak — JSON в 100× быстрее, без CF-обхода.
