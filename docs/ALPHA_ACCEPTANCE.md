# Alpha runtime and release acceptance

Target: **2.0.0-alpha.1, unreleased, not production-hardened**. See
[implementation status](IMPLEMENTATION_STATUS.md) for measured results and exact
source. PR #15 is the open dependency, not an assumed merged baseline.

## Reproduce the gates

Use Linux amd64 Docker Engine with Compose, Python 3.11+, Node 22 and sufficient
capacity for thirteen small services plus Chromium. No paid service is required.
Do not point these tests at an existing deployment. From the checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[postgres,test,acceptance]' pip-audit
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/pytest -o addopts= -q -ra
.venv/bin/pytest --run-integration tests/integration -v --tb=short
.venv/bin/pytest --run-acceptance tests/acceptance -v --junitxml=evidence/acceptance/junit.xml
python3 scripts/scan_images.py --output evidence/containers
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m pip check
.venv/bin/python scripts/dependency_audit.py python --output evidence/dependencies/python
for d in app1-blast-radius/frontend app2-behavior-baseline/frontend app3-code-provenance/frontend app4-mcp-scorecard/frontend; do
  (cd "$d" && npm ci --ignore-scripts && node --test ../../tests/frontend/pdf-export.test.cjs && npm run build) || exit 1
  python3 scripts/dependency_audit.py npm --directory "$d" --output "evidence/dependencies/$(dirname "$d")" || exit 1
done
```

Default pytest explicitly skips integration/acceptance: those skips are NOT
passing gates. Missing Docker, browser, scanner database or startup failures fail
their explicit jobs. The installed application images have no pytest/Playwright
or editable source installation; test tools live only on the runner.

`AcceptanceStack` resolves the **root Compose file** using fresh generated dummy
credentials, then gives resources unique `atp-acceptance-*` names and ephemeral
loopback ports. Healthcheck frequency and CPU/memory limits are test-only overrides.
A read-only initialization SQL fixture delays the temporary PostgreSQL server;
the real health check must wait for final TCP readiness, avoiding premature workers.
Real API, Nginx, worker, PostgreSQL and Redis services are used. No HTTP route
interception replaces them. Provider keys are absent and hosted analysis disabled;
unit/contracts separately simulate optional-provider errors. Live hosted providers
are **untested**. Build/package-registry and scanner-database traffic is expected;
browser requests must stay on loopback and key-only legacy provider tests forbid
outbound network attempts. This is not a production network-egress certification.

Evidence includes build/service logs (dummy secrets redacted), source SHA and
dirty-source flag, image IDs/digests, browser traces/screenshots, actual PDF
downloads and extracted page images. Tests check source findings, rendered graph
elements, PDF page bounds and nonblank content throughout report images. Inspect
the images too: checking a PDF header or length alone is insufficient. Reports
are rasterized legacy exports, not accessible/searchable-text PDF certification.
Behavior's seeded-demo workspace has neither a submission form nor report download;
its selection, chart/timeline, real ingest API, errors and demo labels are covered.

## Installation and data

README quick start is the fresh-install path: `configure_local.py`, deployment
preflight, then `docker compose up --build -d --wait`. The test executes these same
configuration/build/start operations with unique resources, not README default
ports or existing project volumes. The generator creates mode-0600 `.env` and
refuses overwrites. `.env.example` is reference only, not usable credentials.

For existing installs, retain `POSTGRES_USER`, `POSTGRES_DB`, password and volume
names. Set a new random API token if the old value was a placeholder. Merely
changing `POSTGRES_PASSWORD` does not rotate an initialized PostgreSQL password.
`SECRET_KEY` is a legacy alias, **not** legacy route authentication.

No new SQL schema is introduced: migrate 001 → 002 → 003 with the installed
runtime, verify old completed jobs and unrelated records, repeat migrations, and
check the backfilled assessment projection. Tests force-recreate API/worker/PG
containers while retaining their unique named volumes and compare result/attempt
values. Prior integration tests independently cover restart and worker death.
`pg_dump -Fc` / `pg_restore --exit-on-error` exercise a separate disposable restore
database; dumps contain only dummy fixtures and are not uploaded.

Before any real upgrade: stop modular writers, retain deployed SHA/image/config,
take a custom-format PostgreSQL backup using your existing private credential
mechanism, and test restore separately. See [runtime rollback](RUNTIME_VALIDATION.md#upgrade-and-rollback).
Do not mix old/new workers or restore over live data. Preserve current data and
restore the pre-upgrade backup into a separate database if rollback is required;
reconcile post-backup records before switching. No operator data was backed up or
modified by this slice. Expired legacy Redis results are unrecoverable.

Teardown runs `compose down` **without `-v`**, then inspects and removes only exact
volumes whose ownership label equals that test's unique project. Dummy data is
intentionally discarded. Only this test's image tags are removed. Never prune or
glob-delete volumes. If interrupted, inspect exact labeled leftovers first.

## Deployment boundaries

Database/cache ports are not published. All other default ports are loopback.
The four legacy APIs/UIs are **unauthenticated local-only demonstrations**; do not
expose them via tunnel, public proxy or port override. No shared SaaS claim.
The modular API has token/scoped/server-bound ownership. Preflight rejects weak
placeholder tokens, unauthenticated platform mode and nonlocal legacy bindings.
For a separately reviewed nonlocal modular API, an explicit Compose override must
set `AGENT_TRUST_ALLOW_REMOTE=true`, a strong token, restrictive CORS and a trusted
TLS proxy. That flag only acknowledges preflight intent; it does not install TLS
or authorize public legacy exposure. Remote deployment is not validated here.
Run preflight on the **resolved configuration including all overrides**:

```bash
docker compose config --format json | python3 scripts/validate_deployment.py
```

Do not print/upload resolved Compose JSON: it contains credentials. No application
container mounts a host Docker socket. Provider opt-in does not certify safe egress
for arbitrary endpoints; legacy URL collectors and broader retention/authorization
hardening remain limitations. Source is analyzed as data, never executed.

## Container evidence and publication

Inventory: five API services, two workers, four Nginx frontends, PostgreSQL 15 and
Redis 7. Build stages use Node 22; production dependency closure/build inventory
is generated with `npm sbom --sbom-format=cyclonedx`, retained in the frontend
image, and included in the image scanner's CycloneDX output. Both OS and application
packages are scanned. No checksum manifest is represented as an SBOM.

The scanner is official Trivy 0.74.0 pinned by image digest in `scan_images.py`.
Method references: [Trivy image scanning](https://trivy.dev/docs/latest/guide/target/container_image/),
[Playwright containers](https://playwright.dev/python/docs/docker), and
[pip vendoring policy](https://pip.pypa.io/en/latest/development/vendoring-policy/).
Only its database download has network access; image archives are processed
offline in a bounded container with **no Docker socket or host credentials**.
It runs as the invoking UID/GID so cache/evidence files stay runner-owned. Alpine
package updates retry at most three times for transient CDN failures; TLS checks,
fresh repository requirements and failure exits remain enabled.
Record scanner version/digest, database UpdatedAt/DownloadedAt (max age 48 hours),
source SHA, dirty flag, image identities, exact commands, full findings, CycloneDX
components and SHA-256 file checksums. Scan reports are time-sensitive evidence,
not a permanent assertion of safety. Full findings include low/medium severity;
owner policy makes dependency findings **informational**, including HIGH/CRITICAL
and unfixed findings. Status: "Accepted for development/alpha; hardening deferred."
No ignore files, hidden findings or clean-scan claim. Scanner execution, stale DB,
missing inventory and invalid reports still fail. See [known issues](KNOWN_SECURITY_ISSUES.md).

Refresh the accepted-risk register from a downloaded, complete artifact without
altering its raw reports. Supply the actual run/artifact identity (the generator
verifies all checksums and records those identities rather than a fixed old run):

```bash
python3 scripts/record_security_findings.py --evidence evidence/connector-ci-containers --run-id 34671947014 --artifact-id 10291645171
```

This records findings; it does not remediate them or approve publication.

CI keeps existing Python, PostgreSQL, four frontend, Compose and audit jobs and
adds `full-stack-acceptance` / `container-security`. Pinned upload-artifact retains
non-sensitive evidence for 14 days even on failure. Download it before expiry
for any release record. A workflow gate is not proof branch protection exists.
No branch protection, account settings or deployment is modified.

Manual release preparation invokes the complete reusable CI; failure blocks its
checksum step. It never publishes. A maintainer must separately review/merge the
dependent changes, rerun all gates on the exact intended source SHA with fresh
scanner data, review findings/SBOM/checksums and migration notes, and approve
publication. Only then, with separate authorization, create a prerelease/tag and
publish artifacts; never mark alpha latest. Nothing in this slice publishes an
image, package, attestation, tag or release.
