#!/usr/bin/env bash
# Run the static site locally with the same html_handling semantics as
# production (Cloudflare Workers Assets). Serves at http://localhost:8787
# by default; pass --port N to override.
#
# Blocks in the foreground; Ctrl+C cleanly shuts down wrangler and its
# workerd children. (npx alone is unreliable at signal forwarding, so we
# manage it explicitly.)
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

wrangler_pid=
cleanup() {
  trap - INT TERM EXIT
  if [[ -n "$wrangler_pid" ]] && kill -0 "$wrangler_pid" 2>/dev/null; then
    # Kill the whole process group so workerd and any other descendants
    # die with wrangler, not just the npx wrapper.
    kill -INT -- "-$wrangler_pid" 2>/dev/null || kill -INT "$wrangler_pid" 2>/dev/null || true
    wait "$wrangler_pid" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

# `setsid` puts wrangler in its own process group so we can signal the
# whole tree above. On macOS without setsid we fall through to a plain run.
if command -v setsid >/dev/null 2>&1; then
  setsid env \
    CLOUDFLARE_API_TOKEN="${CLOUDFLARE_WORKERS_API_TOKEN:-}" \
    CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_WORKERS_ACCOUNT_ID:-}" \
    npx -y wrangler@latest dev "$@" &
else
  env \
    CLOUDFLARE_API_TOKEN="${CLOUDFLARE_WORKERS_API_TOKEN:-}" \
    CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_WORKERS_ACCOUNT_ID:-}" \
    npx -y wrangler@latest dev "$@" &
fi
wrangler_pid=$!
wait "$wrangler_pid"
