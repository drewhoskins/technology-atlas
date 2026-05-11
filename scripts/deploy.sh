#!/usr/bin/env bash
# Deploy the static site to Cloudflare Workers.
#
# Loads credentials from .env (managed by `stripe projects env --pull`)
# and remaps SP's per-service variable names to the canonical names
# wrangler expects.

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "error: .env not found — run 'stripe projects env --pull' first" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

CLOUDFLARE_API_TOKEN="$CLOUDFLARE_WORKERS_API_TOKEN" \
CLOUDFLARE_ACCOUNT_ID="$CLOUDFLARE_WORKERS_ACCOUNT_ID" \
exec npx -y wrangler@latest deploy "$@"
