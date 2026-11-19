#!/usr/bin/env bash
# Stops the pipeline's model-calling runs before they spill into paid overage.
#
# The Claude Code CLI does not refuse calls when a subscription limit is used up
# and overage is allowed; it keeps going at extra cost, and the JSON result does
# not say so. Only the stream output carries the limit status. This asks for it
# with one tiny call every INTERVAL seconds and, when the limit is close or
# overage is in use, kills the runs and exits.
#
#   scripts/limit_watch.sh [max_utilization=0.90] [interval_seconds=600]
set -u
MAX="${1:-0.90}"
INTERVAL="${2:-600}"
LOG="${AIOMIM_LIMIT_LOG:-runs/limit_watch.log}"
PATTERN='aiomim\.cli (run|secondhand-check|guide-learn|gaps|editorial|reconcile-check|backtest|update|adjudicate|audit-check|create)'

probe() {
  (cd "${TMPDIR:-/tmp}" && echo "Reply with the single word: ok" | timeout 120 claude -p --model claude-haiku-5-5 \
      --output-format stream-json --verbose --tools "" --strict-mcp-config --setting-sources "" \
      --disable-slash-commands --no-session-persistence 2>/dev/null) | python3 -c '
import sys, json
info = None
for line in sys.stdin:
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("type") == "rate_limit_event":
        info = d.get("rate_limit_info") or {}
if info is None:
    print("unknown 0 unknown")
else:
    windows = info.get("unifiedWindows") or {}
    used = max([float(w.get("utilization") or 0) for w in windows.values()] or [0.0])
    print("overage" if info.get("isUsingOverage") else "ok", used, info.get("status", "unknown"))
'
}

while true; do
  read -r state used status <<<"$(probe)"
  echo "$(date -u +%H:%M) state=$state utilization=$used status=$status" >> "$LOG"
  if [ "$state" = "overage" ] || [ "$status" = "rejected" ] || python3 -c "import sys; sys.exit(0 if float('$used') >= float('$MAX') else 1)"; then
    pkill -f "$PATTERN" && killed=yes || killed=no
    echo "STOPPED RUNS: state=$state utilization=$used status=$status (runs killed: $killed)"
    exit 3
  fi
  sleep "$INTERVAL"
done
