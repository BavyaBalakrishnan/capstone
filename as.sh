# AgentSwitch shell helpers.  Source it, do not run it:
#
#     source as.sh
#     as_use suryodaya      # or: as_use keystone
#     as_login
#     as_me
#
# The password is read from .env and never appears in a command line, so it
# stays out of shell history and out of `ps`.

AS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

_as_loadenv() {
  [ -f "$AS_DIR/.env" ] || { echo "no .env — copy .env.example to .env first" >&2; return 1; }
  set -a; . "$AS_DIR/.env"; set +a
}

as_use() {
  case "$1" in
    suryodaya|india|in) export AS=https://agentswitch.theschoolofai.in
                        export AS_NAME=suryodaya ;;
    keystone|us)        export AS=https://class.agentswitch.theschoolofai.in
                        export AS_NAME=keystone ;;
    *) echo "usage: as_use suryodaya|keystone" >&2; return 1 ;;
  esac
  unset TOKEN
  echo "$AS_NAME  ->  $AS   (token cleared, run as_login)"
}

as_login() {
  _as_loadenv || return 1
  [ -n "$AS" ] || { echo "run as_use first" >&2; return 1; }

  local pw
  case "$AS_NAME" in
    suryodaya) pw="$AS_PASSWORD_SURYODAYA" ;;
    keystone)  pw="$AS_PASSWORD_KEYSTONE" ;;
  esac
  [ -n "$pw" ] || { echo "no password for $AS_NAME in .env" >&2; return 1; }

  # Body goes in via stdin (@-), so the password is never an argv entry.
  local resp
  resp=$(AS_PW="$pw" python3 -c '
import json, os, sys
sys.stdout.write(json.dumps({"email": os.environ["AS_EMAIL"],
                             "password": os.environ["AS_PW"]}))' \
    | curl -s -X POST "$AS/api/auth/login" \
           -H 'Content-Type: application/json' --data-binary @-)

  export TOKEN=$(printf '%s' "$resp" | jq -r '.token // empty')
  if [ -z "$TOKEN" ]; then
    echo "login failed on $AS_NAME:" >&2
    printf '%s\n' "$resp" | head -c 500 >&2; echo >&2
    return 1
  fi
  echo "logged in to $AS_NAME  (token ${#TOKEN} chars)"
}

# --- REST ---------------------------------------------------------------
# as_rest /api/auth/me
as_rest() {
  curl -s "$AS$1" -H "Authorization: Bearer $TOKEN"
}

as_me() { as_rest /api/auth/me | jq .; }

# --- MCP ----------------------------------------------------------------
# as_mcp tools/list '{}'
#
# A JSON-RPC denial comes back as HTTP 200 with an `error` in the body
# (brief section 6).  This prints a loud marker for that case, because a
# client that only checks the HTTP status reads every denial as success.
as_mcp() {
  local method="$1" params="${2:-{\}}" id=$RANDOM
  local resp
  resp=$(printf '{"jsonrpc":"2.0","id":%s,"method":"%s","params":%s}' \
           "$id" "$method" "$params" \
         | curl -s -X POST "$AS/api/mcp" \
                -H "Authorization: Bearer $TOKEN" \
                -H 'Content-Type: application/json' --data-binary @-)

  printf '%s' "$resp" | jq -e '.error' >/dev/null 2>&1 \
    && echo "### JSON-RPC ERROR (HTTP was still 200) ###" >&2
  printf '%s' "$resp" | jq .
}

as_init() {
  as_mcp initialize '{"protocolVersion":"2025-11-25","capabilities":{},
                      "clientInfo":{"name":"'"${AS_EMAIL%%@*}"'","version":"0.1"}}' >/dev/null
  as_mcp notifications/initialized '{}' >/dev/null 2>&1
  echo "handshake done on $AS_NAME"
}

# as_tools  -> just the tool names, sorted
as_tools() { as_mcp tools/list '{}' | jq -r '.result.tools[].name' | sort; }

echo "loaded. next:  as_use suryodaya  ->  as_login  ->  as_me"
