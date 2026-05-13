#!/bin/sh
# Usage: reddit_hot.sh r/sub limit
SUB="${1:-r/Entrepreneur}"
LIMIT="${2:-10}"
SUB="${SUB#r/}"
curl -sH "User-Agent: hermes-bot/1.0" "https://www.reddit.com/r/$SUB/hot.json?limit=$LIMIT" \
  | jq -r '.data.children[] | "\(.data.score | tostring | .[0:6])\t\(.data.num_comments | tostring | .[0:5])\t\(.data.title[0:80])\thttps://reddit.com\(.data.permalink)"' \
  | column -t -s $'\t'
