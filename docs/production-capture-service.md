# Production screenshot service design

Theme Kit's `ntk capture` command is the supported local and CI path. A hosted capture service is intentionally deferred until the platform team can provide the isolation, storage, and operating controls below.

## Proposed contract

- `POST /api/admin/themes/{theme_id}/captures/` accepts an allowlisted store route, the fixed `desktop` and/or `mobile` viewports, and an optional theme revision.
- The API authenticates with `themes:read`, resolves only the tenant's network domain, rejects arbitrary hosts and private-network destinations, and returns `202` with a job ID.
- A sandboxed Chromium worker opens the preview URL with `skip_cache=1`, waits for network idle, fonts, lazy media, and decoded images, then writes 1440px and 390px full-page PNGs.
- Artifacts are content-addressed, encrypted, tenant-scoped, retained for seven days, and returned through short-lived signed URLs. Logs redact query secrets and cookies.
- Jobs have a 60-second wall-clock limit, strict memory/response-size caps, per-store concurrency and rate limits, idempotency keys, cancellation, and auditable failure codes.
- The result records theme ID/revision, route, viewport dimensions, capture timestamp, browser version, artifact hash, and final response `X-Theme-*` headers.

## Delivery slices

1. Reuse the deterministic wait and viewport contract from `ntk capture` in a container image.
2. Add the authenticated job API and queue with SSRF and tenant-isolation tests.
3. Add artifact storage, signed delivery, retention cleanup, and operational dashboards.
4. Dogfood against Spark route matrices before exposing the service outside platform engineering.

The tracking issue linked from the Theme Kit pull request owns this follow-up. Until it ships, CI should install `next_theme_kit[capture]`, install Chromium, and retain `qa-output/*.png` as build artifacts.
