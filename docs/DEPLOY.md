# Deploying technologyatlas.org on Cloudflare Pages

The site is a static bundle under `web/` produced by `scripts/build_site.py` and
committed to the repo. Hosting is Cloudflare Pages, connected to GitHub
`drewhoskins/technology-atlas`. The domain `technologyatlas.org` is registered
at GoDaddy; DNS is delegated to Cloudflare.

This runbook covers the one-time setup. After it's in place, `git push` to
`main` is the entire deploy.

## Prerequisites

- Cloudflare account with access to add a zone.
- GoDaddy account with admin on `technologyatlas.org`.
- GitHub account with admin on `drewhoskins/technology-atlas`.

## 1. Add the zone to Cloudflare

1. Cloudflare dashboard → **Add a site** → enter `technologyatlas.org`.
2. Pick the Free plan.
3. Cloudflare scans existing DNS at GoDaddy. There are no records to preserve
   (the domain has not been used), so the import can be empty.
4. Cloudflare shows two assigned nameservers, e.g.
   `xxx.ns.cloudflare.com` and `yyy.ns.cloudflare.com`. Copy both.

## 2. Repoint nameservers at GoDaddy

1. GoDaddy → **My Products** → `technologyatlas.org` → **DNS** → **Nameservers**
   → **Change**.
2. Choose **Enter my own nameservers** and paste the two Cloudflare hosts.
3. Save. GoDaddy may warn about leaving their DNS; that's expected.
4. Back in Cloudflare, click **Done, check nameservers**. Propagation is
   typically minutes to a few hours; Cloudflare emails when the zone is active.

## 3. Create the Pages project

1. Cloudflare dashboard → **Workers & Pages** → **Create application** →
   **Pages** → **Connect to Git**.
2. Authorize Cloudflare on GitHub and select `drewhoskins/technology-atlas`.
3. Configure the build:
   - **Production branch**: `main`
   - **Framework preset**: None
   - **Build command**: *(leave empty)*
   - **Build output directory**: `web`
   - **Root directory**: *(leave empty)*
4. Save and deploy. First deploy serves at
   `technology-atlas.pages.dev` (or similar). Confirm the homepage and a few
   entry pages render correctly before wiring the custom domain.

## 4. Attach the custom domain

1. In the Pages project → **Custom domains** → **Set up a custom domain**.
2. Add `technologyatlas.org`. Cloudflare creates the CNAME/AAAA records in the
   zone automatically because DNS is delegated.
3. Add `www.technologyatlas.org` the same way, or set up a redirect (see §6).
4. Wait for the certificate to issue (usually under a minute). Visit
   `https://technologyatlas.org` to confirm.

## 5. Verify

- `https://technologyatlas.org` loads the homepage.
- `https://technologyatlas.org/entries/bus.html` loads.
- Cert is valid (Cloudflare-issued).
- Pushing a no-op commit to `main` triggers a new deploy in the Pages
  dashboard within ~30s.

## 6. Optional: apex/www redirect

If `www.technologyatlas.org` should permanently redirect to the apex (or vice
versa), add a Cloudflare **Bulk Redirect** or a single Page Rule. Pick one
canonical host and 301 the other.

## Operating model

- Every push to `main` redeploys automatically. There is no manual step.
- Preview deployments are enabled by default for non-`main` branches and
  produce `<branch>.technology-atlas.pages.dev` URLs.
- To roll back: Pages → **Deployments** → pick a prior successful deploy →
  **Rollback to this deployment**. (Faster than reverting a commit.)
- The build output `web/` is committed, so the site can also be served from
  any other static host (S3+CloudFront, Netlify, GitHub Pages) without
  changes if Cloudflare is ever swapped out.

## Troubleshooting

- **Nameserver change not detected after several hours.** Re-check the two
  hosts at GoDaddy match exactly what Cloudflare assigned; GoDaddy sometimes
  silently appends a trailing dot or drops one.
- **Pages deploy succeeds but homepage 404s.** Confirm **Build output
  directory** is `web`, not the repo root.
- **Custom domain stuck on "Verifying".** The zone must be active in
  Cloudflare first (§2). Pages won't issue a cert against a pending zone.
