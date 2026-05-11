# Deploying technology-atlas on Cloudflare Workers

The site is a static bundle under `web/` produced by `scripts/build_site.py`
and committed to the repo. Hosting is Cloudflare Workers Static Assets,
provisioned via the Stripe Projects CLI. The custom domain
`technologyatlas.org` is deferred — v1 serves at `<worker>.workers.dev`.

This runbook covers the one-time setup. After it's in place, `git push` to
`main` is the entire deploy.

## Where things stand

Stripe Projects has already:

- Linked a Cloudflare account.
- Provisioned the `workers:free` plan and the `workers` service.
- Written Cloudflare API credentials to `.env`.

Confirm with `stripe projects status`. The remaining work is the three
sections below.

## 1. Add `wrangler.toml`

At repo root, create `wrangler.toml`:

```toml
name = "technology-atlas"
compatibility_date = "2026-05-10"

[assets]
directory = "./web"
```

The Worker name becomes part of the public URL:
`technology-atlas.<account>.workers.dev`. No `not_found_handling` is set;
every entry is a real file in `web/`, so the default 404 behavior is
correct.

## 2. First deploy from the CLI

Source the credentials and deploy via `npx`:

```bash
set -a; source .env; set +a
npx wrangler deploy
```

The first invocation will offer to install `wrangler`; accept it. On
success, the output prints the live URL. Verify:

- Homepage renders at `https://technology-atlas.<account>.workers.dev`.
- A category page (`/entries/bus.html`) and an entry page
  (`/entries/bus__horse_omnibus.html`) both render.
- Styles load (no flash of unstyled HTML).

If any of those fail, see **Troubleshooting** below before moving on.

## 3. Wire up auto-deploy from GitHub

Manual `wrangler deploy` is fine for an emergency, but every push to
`main` should redeploy. Workers Builds (the GitHub integration in the
Cloudflare dashboard) handles this:

1. Cloudflare dashboard → **Workers & Pages** → `technology-atlas` →
   **Settings** → **Builds**.
2. Connect the GitHub repo `drewhoskins/technology-atlas`.
3. Production branch: `main`.
4. Build command: *(leave empty)* — `web/` is already built and
   committed.
5. Deploy command: `npx wrangler deploy`.
6. Save. Workers Builds runs inside Cloudflare's environment and is
   pre-authenticated against this account; no token plumbing required.

A no-op commit to `main` should trigger a new deploy in the dashboard
within ~30s.

## Operating model

- Every push to `main` redeploys automatically.
- Preview deployments are created for non-`main` branches and PRs at
  `<branch>.technology-atlas.<account>.workers.dev`.
- Rollback: dashboard → **Deployments** → pick a prior successful deploy
  → **Rollback to this deployment**. Faster than reverting a commit.
- Free-tier quota is 100K requests/day shared across all Workers on the
  account. For an atlas site that's far more than current load; the
  upgrade path if it ever matters is `workers:paid` (~$5/month minimum)
  via `stripe projects upgrade cloudflare-plan workers:paid`.
- The output `web/` is committed, so the site can also be served from
  any other static host without changes if Workers is ever swapped out.

## Deferred: custom domain

Once verified at `*.workers.dev`, wiring `technologyatlas.org` is two
steps:

1. Add the zone to Cloudflare (GoDaddy stays as registrar; its
   nameservers point at the two Cloudflare hosts shown when the zone is
   added).
2. Worker → **Settings** → **Domains & Routes** → **Add Custom Domain**
   → `technologyatlas.org`.

Cert issuance is automatic once the zone is active.

## Troubleshooting

- **`wrangler deploy` complains it can't find an account or token.**
  Confirm `.env` was sourced in the *current* shell and that
  `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are populated.
  `stripe projects env` shows what's available.
- **Deploy succeeds but every URL returns 404.** Check that `[assets]
  directory = "./web"` in `wrangler.toml`, not the repo root or another
  directory.
- **Styles 404 even though pages load.** `web/styles.css` is referenced
  as `./styles.css` from `web/index.html` — confirm the asset upload
  included the CSS file (`wrangler deploy` lists every file uploaded).
- **Workers Builds fails on git push.** Open the build's logs in the
  dashboard. The most common cause is a transient install failure for
  `wrangler`; retrying the build usually resolves it.
