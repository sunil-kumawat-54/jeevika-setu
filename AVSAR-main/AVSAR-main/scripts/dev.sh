#!/usr/bin/env bash
# make dev — uvicorn --reload + next dev, concurrently, on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/services"
trap 'kill 0' EXIT INT TERM
uvicorn core.main:app --reload --host 0.0.0.0 --port 8000 &
(cd apps/web && npm run dev) &
wait
