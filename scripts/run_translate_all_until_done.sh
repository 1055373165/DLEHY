#!/usr/bin/env bash
# Autonomous 10-book parallel translation loop.
# Runs the supervisor repeatedly with --execute --parallel 10
# until all books report no remaining work.
set -uo pipefail

VENV="/Users/smy/project/book-agent/.venv/bin/python"
SCRIPT="scripts/run_translate_agent_rollout_supervisor.py"
PACKET_LIMIT="${1:-20}"
MAX_ROUNDS="${2:-500}"
LOG_DIR="artifacts/review/translation-loop-logs"
STATE_JSON="artifacts/review/translate-agent-rollout-state-current.json"
mkdir -p "$LOG_DIR"

ROUND=0
ALL_DONE=0

echo "=== AUTONOMOUS TRANSLATION LOOP ==="
echo "Packet limit per book per round: $PACKET_LIMIT"
echo "Max rounds: $MAX_ROUNDS"
echo "Start time: $(date -Iseconds)"
echo ""

while [ "$ROUND" -lt "$MAX_ROUNDS" ] && [ "$ALL_DONE" -eq 0 ]; do
    ROUND=$((ROUND + 1))
    ROUND_LOG="$LOG_DIR/round-$(printf '%04d' $ROUND).json"
    echo "--- Round $ROUND @ $(date '+%H:%M:%S') ---"

    # Run supervisor with execution
    "$VENV" "$SCRIPT" \
        --execute \
        --parallel 10 \
        --packet-limit "$PACKET_LIMIT" \
        > "$ROUND_LOG" 2>&1 || true

    # Parse results from the round log
    STATS=$("$VENV" -c "
import json, sys
try:
    data = json.loads(open('$ROUND_LOG').read())
    results = data.get('results', [])
    succeeded = sum(1 for r in results if r.get('status') == 'succeeded')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    fully_done = 0
    for r in results:
        tail = r.get('stdout_tail', '')
        if '\"fully_translated\": true' in tail:
            fully_done += 1
    print(f'{succeeded},{failed},{fully_done},{len(results)}')
except Exception as e:
    print(f'0,0,0,0', file=sys.stderr)
    print('0,0,0,0')
" 2>/dev/null)

    IFS=',' read -r OK FAIL FULLYDONE TOTAL <<< "$STATS"
    echo "  Executed: $OK ok / $FAIL fail / $TOTAL total | chapters_completed=$FULLYDONE"

    # After execution, run plan-only to check how many books still have work
    PLAN_OUTPUT=$("$VENV" "$SCRIPT" --packet-limit "$PACKET_LIMIT" 2>/dev/null) || true

    # Check state file to determine if all books are done
    REMAINING=$("$VENV" -c "
import json
state = json.loads(open('$STATE_JSON').read())
books = state.get('books', [])
still_working = 0
done_count = 0
benchmark_pending = 0
for b in books:
    action_data = b.get('planned_action', {})
    if not isinstance(action_data, dict):
        still_working += 1
        continue
    action = action_data.get('action', '')
    pilot = b.get('live_pilot', {})
    no_work = pilot.get('no_work_remaining', False) if pilot else False

    if no_work:
        done_count += 1
    elif action in ('benchmark_no_go_hold', 'benchmark_annotation_pending', 'benchmark_manifest_missing'):
        # Stuck on benchmark - count as blocked, not working
        benchmark_pending += 1
        done_count += 1  # Don't wait for these
    elif action == '' or action is None:
        done_count += 1
    else:
        still_working += 1

print(f'{still_working},{done_count},{benchmark_pending}')
" 2>/dev/null)

    IFS=',' read -r WORKING DONE BLOCKED <<< "$REMAINING"
    echo "  Status: $WORKING still translating / $DONE done or blocked / $BLOCKED benchmark-blocked"

    if [ "${WORKING:-99}" -eq 0 ] 2>/dev/null; then
        echo ""
        echo "=== ALL BOOKS COMPLETED OR BLOCKED ==="
        ALL_DONE=1
    fi

    # Brief pause between rounds
    if [ "$ALL_DONE" -eq 0 ]; then
        sleep 3
    fi
done

echo ""
echo "=== LOOP FINISHED ==="
echo "Total rounds: $ROUND"
echo "End time: $(date -Iseconds)"
echo "Final state: $STATE_JSON"

# Print final summary
"$VENV" -c "
import json
state = json.loads(open('$STATE_JSON').read())
books = state.get('books', [])
print()
print('=== FINAL STATUS ===')
for b in books:
    qi = b.get('queue_index', '?')
    src = (b.get('source_path','') or '?').split('/')[-1][:55]
    pilot = b.get('live_pilot', {})
    action_data = b.get('planned_action', {})
    action = action_data.get('action', '?') if isinstance(action_data, dict) else '?'
    no_work = pilot.get('no_work_remaining', False) if pilot else False
    fully = pilot.get('fully_translated', False) if pilot else False
    seq = pilot.get('latest_sequence', 0) if pilot else 0
    status = 'DONE' if no_work else ('TRANSLATING' if 'pilot' in action else action.upper())
    print(f'[{qi}] {status:20s} seq={seq:3d} | {src}')
" 2>/dev/null
