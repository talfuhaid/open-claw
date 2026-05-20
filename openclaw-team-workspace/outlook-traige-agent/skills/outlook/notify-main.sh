#!/bin/bash
set -euo pipefail

export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

case "${1:-}" in
  ""|"-h"|"--help"|"help")
    echo "Usage: notify-main.sh <alert message>" >&2
    exit 2
    ;;
  "HEARTBEAT_OK"|"NO_REPLY")
    echo "Refusing to send non-alert control message: $1" >&2
    exit 2
    ;;
esac

ALERT_TEXT="$*"

case "$ALERT_TEXT" in
  *"Usage:"*|*"command not found"*|*"No such file"*|*"Permission denied"*|*"Traceback"*|*"Error:"*)
    echo "Refusing to send diagnostic/error text as Outlook alert" >&2
    exit 2
    ;;
esac

MESSAGE="Outlook triage alert: $ALERT_TEXT"

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
OUTLOOK_CONFIG="${OUTLOOK_CONFIG:-$HOME/.outlook-mcp/config.json}"
CONFIG="$OPENCLAW_HOME/openclaw.json"
TOKENS="$OPENCLAW_HOME/.tokens"

if [ ! -f "$CONFIG" ]; then
  echo "Error: config not found: $CONFIG" >&2
  exit 1
fi

# Load hook token. Prefer .tokens because entrypoint exports/substitutes from there.
if [ -f "$TOKENS" ]; then
  # shellcheck disable=SC1090
  . "$TOKENS"
fi

HOOK_TOKEN="${HOOKS_TOKEN:-}"

if [ -z "$HOOK_TOKEN" ] || [ "$HOOK_TOKEN" = "null" ]; then
  HOOK_TOKEN="$(jq -r '.hooks.token // empty' "$CONFIG")"
fi

if [ -z "$HOOK_TOKEN" ] || [ "$HOOK_TOKEN" = "null" ]; then
  echo "Error: hooks token missing. Checked $TOKENS and .hooks.token in $CONFIG" >&2
  exit 1
fi

GATEWAY_BIND="$(jq -r '.gateway.bind // .bind // "loopback"' "$CONFIG")"
GATEWAY_PORT="$(jq -r '.gateway.port // .port // empty' "$CONFIG")"

if [ -z "$GATEWAY_PORT" ] || [ "$GATEWAY_PORT" = "null" ]; then
  GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
fi

if [ "$GATEWAY_BIND" = "loopback" ] || [ "$GATEWAY_BIND" = "localhost" ]; then
  GATEWAY_URL="http://127.0.0.1:${GATEWAY_PORT}"
else
  GATEWAY_URL="http://${GATEWAY_BIND}:${GATEWAY_PORT}"
fi

if ! curl -sS --max-time 3 "$GATEWAY_URL/healthz" >/dev/null 2>&1; then
  echo "Error: OpenClaw gateway is not reachable at $GATEWAY_URL" >&2
  echo "Debug:" >&2
  echo "  GATEWAY_BIND=$GATEWAY_BIND" >&2
  echo "  GATEWAY_PORT=$GATEWAY_PORT" >&2
  echo "  CONFIG=$CONFIG" >&2
  exit 1
fi

TELEGRAM_ID=""

if [ -f "$OUTLOOK_CONFIG" ]; then
  TELEGRAM_ID="$(jq -r '.notification_targets.telegram // empty' "$OUTLOOK_CONFIG" 2>/dev/null | head -n 1)"
fi

if [ -z "$TELEGRAM_ID" ] || [ "$TELEGRAM_ID" = "null" ]; then
  TELEGRAM_ID="$(
    jq -r '
      (.session.identityLinks // {})
      | keys[]
      | select(startswith("telegram:"))
      | sub("^telegram:"; "")
    ' "$CONFIG" 2>/dev/null | head -n 1
  )"
fi

if [ -n "$TELEGRAM_ID" ] && [ "$TELEGRAM_ID" != "null" ]; then
  echo "Telegram target linked: $TELEGRAM_ID"

  PAYLOAD="$(jq -n \
    --arg msg "$MESSAGE" \
    --arg to "$TELEGRAM_ID" \
    '{
      message: $msg,
      agentId: "main",
      sessionKey: "agent:main:main",
      deliver: true,
      channel: "telegram",
      to: $to
    }')"
else
  echo "Telegram target not linked; sending to main WebChat session only"

  PAYLOAD="$(jq -n \
    --arg msg "$MESSAGE" \
    '{
      message: $msg,
      agentId: "main",
      sessionKey: "agent:main:main",
      deliver: false
    }')"
fi

RESPONSE="$(curl -sS -w "\n%{http_code}" -X POST "$GATEWAY_URL/hooks/agent" \
  -H "Authorization: Bearer $HOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>&1)"

HTTP_CODE="$(printf '%s\n' "$RESPONSE" | tail -1)"
BODY="$(printf '%s\n' "$RESPONSE" | sed '$d')"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "202" ]; then
  if [ -n "$TELEGRAM_ID" ] && [ "$TELEGRAM_ID" != "null" ]; then
    echo "Sent to agent:main:main with Telegram target $TELEGRAM_ID"
  else
    echo "Sent to agent:main:main only"
  fi
else
  echo "Failed to send alert HTTP=$HTTP_CODE" >&2
  [ -n "$BODY" ] && printf '%s\n' "$BODY" >&2
  exit 1
fi