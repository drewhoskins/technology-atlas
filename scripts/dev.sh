#!/usr/bin/env bash
# Run the static site locally with the same html_handling semantics as
# production (Cloudflare Workers Assets). Serves at http://localhost:8787
# by default; pass --port N to override.
#
# Use this instead of opening web/index.html via file:// — file:// has no
# URL-rewriting layer, so extensionless hrefs (e.g., /entries/bus) won't
# resolve to web/entries/bus.html the way Cloudflare does.

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

CLOUDFLARE_API_TOKEN="${CLOUDFLARE_WORKERS_API_TOKEN:-}" \
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_WORKERS_ACCOUNT_ID:-}" \
exec npx -y wrangler@latest dev "$@"
