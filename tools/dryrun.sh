#!/bin/bash
#
# One graded-style dry run, one instance, against the real instance.
#
#   tools/dryrun.sh suryodaya            # output in runs_local/suryodaya-<date>
#   tools/dryrun.sh keystone mytag
#
# Written after a day (2026-10-19) in which four separate run attempts measured
# something other than the agent. Each line below that looks fussy is there
# because its absence cost us a run:
#
#   * ONE login, minted here and passed in as AGENTSWITCH_TOKEN. The runner
#     builds a fresh write client per task and the grid runs two arms, so a
#     17-task run logged in more than thirty times in a minute and the login
#     endpoint began returning 401 and then 429.
#
#   * NO AGENTSWITCH_BASE_URL. The hosts differ per instance:
#         suryodaya -> agentswitch.theschoolofai.in
#         keystone  -> class.agentswitch.theschoolofai.in
#     Hardcoding the class host pointed every Suryodaya run at KEYSTONE's
#     instance while holding a Suryodaya token. Reads succeeded and returned
#     the wrong book, so a run labelled suryodaya reported 150 tickets for a
#     103-ticket instance. client.py now refuses this, but do not re-add it.
#
#   * env -i, so nothing in the ambient shell leaks in and quietly changes
#     which instance or model is used.
#
#   * A copy of the tree, so editing the repo mid-run cannot change what is
#     being measured.
#
# Run ONE instance at a time. Two at once compete for the same model key, and
# exhausting its quota is how an evening ends.
set -u
INST="${1:-}"
case "$INST" in
  suryodaya|keystone) ;;
  *) echo "usage: tools/dryrun.sh {suryodaya|keystone} [tag]" >&2; exit 2 ;;
esac
TAG="${2:-$(date +%Y%m%d-%H%M)}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

TOK=""
for wait in 0 120 180 240 300 300; do
  [ "$wait" -gt 0 ] && { echo "login refused; backing off ${wait}s"; sleep "$wait"; }
  TOK=$(python -c "
from seat15.harness.client import Client
try:
    print(Client('$INST').login())
except Exception:
    print('')
" 2>/dev/null | tr -d '\r')
  [ -n "$TOK" ] && { echo "token minted (backoff ${wait}s)"; break; }
done
if [ -z "$TOK" ]; then
  echo "LOGIN STILL REFUSED after backoff - did not run." >&2
  echo "The login endpoint rate-limits. Wait, do not retry in a loop." >&2
  exit 1
fi

OUT="$ROOT/runs_local/$INST-$TAG"
rm -rf "$OUT"; mkdir -p "$OUT"
cp -r seat15 agentswitch-harness.toml requirements.txt "$OUT/"

LLM=$(python -c "
from seat15.harness.client import load_env
e = load_env()
print('%s|%s|%s' % (e['SEAT15_LLM_BASE_URL'], e['SEAT15_LLM_API_KEY'],
                    e['SEAT15_LLM_MODEL']))")
IFS='|' read -r LB LK LM <<< "$LLM"

cd "$OUT" || exit 1
START=$(date +%s)
# SEAT15_* flags pass through so an arm can be measured against the
# default without editing this script. env -i drops everything else on
# purpose, which on 2026-10-27 meant a run launched with
# SEAT15_SEMANTIC_KB=1 silently measured the default instead.
env -i PATH="$PATH" SYSTEMROOT="${SYSTEMROOT:-}" \
  SEAT15_SEMANTIC_KB="${SEAT15_SEMANTIC_KB:-}" \
  SEAT15_CACHE_DIR="${SEAT15_CACHE_DIR:-$ROOT/.cache}" \
  AGENTSWITCH_TOKEN="$TOK" AGENTSWITCH_INSTANCE="$INST" \
  OPENAI_BASE_URL="$LB" OPENAI_API_KEY="$LK" OPENAI_MODEL="$LM" \
  python -u -m seat15.harness.official > run.log 2>&1
echo "elapsed $(( ($(date +%s) - START) / 60 ))m   ($OUT)"
tail -30 run.log
