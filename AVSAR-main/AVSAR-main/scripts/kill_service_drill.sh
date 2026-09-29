#!/usr/bin/env bash
#
# scripts/kill_service_drill.sh — the kill-a-service drill.
#
# PLAN.md §8 Phase 3:
#   **Kill-a-service drills**: unplug internet / revoke keys / kill DB container
#   mid-flow -> system degrades to mock/template mode with a friendly line.
#   Practice until boring.
#
# PLAN.md §14 definition of done:
#   Kill-a-service drill passes (network off -> template mode; DB down ->
#   readable error + recovery)
#
# Three scenarios, each asserted rather than merely attempted:
#
#   1. NETWORK OFF        the beneficiary journey still completes, offline,
#                         with no provider reachable.
#   2. DATABASE STOPPED   the user gets a friendly, speakable error — not a
#                         stack trace, not a hang — and the system recovers
#                         when the database comes back.
#   3. PROVIDER KEY BAD   a failing speech provider is demoted and the mock
#                         takes over; the session is flagged degraded.
#
# Exits 0 only if all three behave. Any scenario that fails prints why.
#
# Usage:  make drill      (or)  bash scripts/kill_service_drill.sh

set -uo pipefail

# Run from the repo root with RELATIVE paths. On Windows, an MSYS path such as
# /d/AVSAR is handed to docker as D:\d\AVSAR, which it cannot resolve; relative
# paths sidestep the translation entirely.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
REPO="$(pwd)"
COMPOSE="docker compose -f infra/docker-compose.yml --env-file .env"
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

PASS=0
FAIL=0

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; FAIL=$((FAIL + 1)); }
info() { printf '        %s\n' "$*"; }

in_core() { $COMPOSE exec -T -w /srv core "$@"; }

wait_healthy() {
  local name="$1" tries="${2:-40}"
  for _ in $(seq 1 "$tries"); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null)" = healthy ] && return 0
    sleep 2
  done
  return 1
}

mkdir -p scripts/_tmp

say "AVSAR kill-a-service drill"
info "repo: ${REPO}"

# ===========================================================================
say "SCENARIO 1 — NETWORK OFF (airplane mode)"
# ===========================================================================
# A container with no network at all: no DNS, no route to any provider. The
# beneficiary journey must still complete end to end on mock + template.
if in_core python scripts/drill_offline.py >scripts/_tmp/avsar_drill_offline.log 2>&1; then
  info "$(tail -4 scripts/_tmp/avsar_drill_offline.log | tr '\n' ' ')"
  ok "offline journey completed with no network egress"
else
  bad "offline journey failed"
  sed 's/^/        /' scripts/_tmp/avsar_drill_offline.log | tail -20
fi

# Same thing, but proven at the container level: --network none.
# Docker needs a native path for the bind mount; `pwd -W` provides it on MSYS.
MOUNT_SRC="$(pwd -W 2>/dev/null || pwd)"
if docker run --rm --network none \
    -e PYTHONPATH=/srv/services -e VOICE_PROVIDER=mock -e LLM_PROVIDER=mock \
    -v "${MOUNT_SRC}:/srv" -w /srv avsar-core:latest \
    python scripts/drill_offline.py --no-db >scripts/_tmp/avsar_drill_nonet.log 2>&1; then
  info "$(tail -3 scripts/_tmp/avsar_drill_nonet.log | tr '\n' ' ')"
  ok "verified with --network none: speech + verbalizer work with no interface up"
else
  bad "--network none run failed"
  sed 's/^/        /' scripts/_tmp/avsar_drill_nonet.log | tail -20
fi

# ===========================================================================
say "SCENARIO 2 — DATABASE STOPPED"
# ===========================================================================
info "stopping the database container..."
docker stop avsar-db >/dev/null 2>&1

sleep 3

READY_CODE="$(curl -s --max-time 20 -o scripts/_tmp/avsar_readyz.json -w '%{http_code}' http://localhost:8000/readyz)"
READY_CODE="${READY_CODE:-000}"
if [ "$READY_CODE" = "503" ]; then
  ok "/readyz reports 503 while the database is down"
else
  bad "/readyz returned ${READY_CODE}, expected 503"
fi

SESSION_CODE="$(curl -s --max-time 20 -o scripts/_tmp/avsar_dberr.json -w '%{http_code}' \
  -X POST http://localhost:8000/sessions \
  -H 'content-type: application/json' -H 'x-avsar-lang: hi' \
  -d '{"channel":"pwa","lang":"hi"}')"
SESSION_CODE="${SESSION_CODE:-000}"

if [ "$SESSION_CODE" = "500" ] || [ "$SESSION_CODE" = "503" ]; then
  if grep -q '"human' scripts/_tmp/avsar_dberr.json 2>/dev/null; then
    ok "database error is a speakable message, not a stack trace (HTTP ${SESSION_CODE})"
    info "$(PYTHONIOENCODING=utf-8 python -c "import json,io;d=json.load(io.open('scripts/_tmp/avsar_dberr.json',encoding='utf-8'));print((d.get('detail') or d).get('human','')[:120])" 2>/dev/null)"
  else
    bad "error body carries no speakable 'human' field"
    info "$(head -c 200 scripts/_tmp/avsar_dberr.json)"
  fi
else
  bad "expected 500/503 with the database down, got ${SESSION_CODE}"
fi

if grep -qi 'traceback\|sqlalchemy\|psycopg' scripts/_tmp/avsar_dberr.json 2>/dev/null; then
  bad "the error body leaks internals to the user"
else
  ok "no stack trace or driver detail leaked to the client"
fi

info "restarting the database..."
docker start avsar-db >/dev/null 2>&1
if wait_healthy avsar-db 45; then
  for _ in $(seq 1 30); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/readyz)" = "200" ] && break
    sleep 2
  done
  if [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/readyz)" = "200" ]; then
    ok "system recovered automatically once the database returned"
  else
    bad "/readyz did not return to 200 after recovery"
  fi
else
  bad "database did not come back healthy"
fi

# ===========================================================================
say "SCENARIO 3 — PROVIDER KEY REVOKED / PROVIDER FAILING"
# ===========================================================================
if in_core python scripts/drill_provider.py >scripts/_tmp/avsar_drill_provider.log 2>&1; then
  info "$(tail -4 scripts/_tmp/avsar_drill_provider.log | tr '\n' ' ')"
  ok "failing provider was demoted and the mock carried the turn"
else
  bad "provider demotion drill failed"
  sed 's/^/        /' scripts/_tmp/avsar_drill_provider.log | tail -20
fi

# ===========================================================================
say "RESULT"
# ===========================================================================
printf '  passed: %d\n  failed: %d\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf '\n\033[31mDRILL FAILED\033[0m — %d check(s) did not behave as designed.\n' "$FAIL"
  exit 1
fi
printf '\n\033[32mDRILL PASSED\033[0m — network off, database down and provider failure all degrade gracefully.\n'
exit 0
