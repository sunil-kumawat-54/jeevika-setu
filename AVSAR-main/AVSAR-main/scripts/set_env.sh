#!/usr/bin/env bash
# set_env.sh KEY VALUE — idempotently set a key in the repo .env
set -euo pipefail
KEY="$1"; VALUE="$2"
ENV_FILE="$(dirname "$0")/../.env"
[ -f "$ENV_FILE" ] || cp "$(dirname "$0")/../.env.example" "$ENV_FILE"
if grep -qE "^${KEY}=" "$ENV_FILE"; then
  # portable in-place edit (GNU + BSD sed)
  tmp="$(mktemp)"
  sed -E "s|^${KEY}=.*|${KEY}=${VALUE}|" "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
else
  printf '\n%s=%s\n' "$KEY" "$VALUE" >> "$ENV_FILE"
fi
echo "set ${KEY}=${VALUE}"
