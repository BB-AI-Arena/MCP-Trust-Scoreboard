# Changelog

## Unreleased

- Apply owner-authorized development/alpha dependency-risk acceptance. Keep raw
  scans/SBOMs and a complete known-issues register; findings are informational,
  scanner execution failures remain blocking. No automatic merge/publication.
- Resume connector-framework/reference-path work; defer image hardening.

- Add actual thirteen-service Compose/Chromium acceptance, PDF content/layout
  evidence, installed-runtime recreation, old-schema upgrade and separate backup
  restore gates. Preserve all existing unit/PostgreSQL checks.
- Repair legacy image contexts, same-origin Nginx routing, mixed-worker async
  handling, atomic Redis publication, behavior API mapping and report capture.
- Keep services loopback-only, remove published database/cache ports, generate
  private fresh-install credentials and require hosted-provider opt-in. Remove
  external font requests; no cosmetic redesign or new product integrations.
- Generate real CycloneDX inventories and scan built OS/application images in CI;
  retain complete evidence. Dependency findings are informational under the
  subsequent owner-approved alpha policy; do not claim a clean scan.

- Fix slotted `Settings.from_env()` defaults; install Uvicorn at runtime and
  preserve the `postgresql://` environment alias with psycopg.
- Apply serialized packaged PostgreSQL migrations; scope job idempotency to
  workspace and repair assessment projections from existing durable results.
- Synchronize job/result writes atomically; fence expired workers and bound
  retries after worker death, including time spent waiting on row locks.
- Add real container/HTTP/PostgreSQL startup, upgrade, recovery, authorization,
  and persisted-result regression gates; readiness now queries the database.
- Update all four frontend lockfiles (jsPDF 4.2.1, Vite 6.4.3 and patched
  transitives), preserving audit thresholds and testing PDF export APIs.
- Gate manual release evidence on exact source and full CI. Checksums do not
  certify release readiness. No new features or UI changes in this repair slice.

- Begin vendor-neutral Agent Trust Platform migration on branch
  `feat/agent-trust-platform-v2-alpha1`.
- Add namespaced domain/provider/storage/API contracts and local security
  regression tests.

No release, tag, package, or container image has been published for this work.
