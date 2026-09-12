# Implementation status

## Owner policy change — development/alpha

Known third-party dependency CVEs are **Accepted for development/alpha; hardening
deferred.** This supersedes earlier zero-HIGH/CRITICAL gate instructions. Do not
restart the container-hardening loop. Alpha is not production-hardened.

Dependency scans/raw reports/SBOMs remain; findings are informational. Scanner
execution, inventory, build, runtime, migration, data-integrity and committed-secret
failures still block. Review/approval, merge, deployment and publication remain
separate states; none are automatic.

Starting SHA: `6f9cdb8d8aac35b5647288200ecff16f31183fab`. PR #15 and #16 were
rechecked and remain open/unmerged at their previously reported heads. Policy
branch `chore/alpha-dependency-risk-policy` depends on `test/alpha-release-acceptance`
(PR #16), not main. Target remains unreleased `2.0.0-alpha.1`.

The interrupted image experiment is preserved locally on
`fix/python-runtime-images`, commit `3e2eb28`; no experimental Dockerfile changes
are carried into this policy/product branch. Its 54 unit tests passed; its full
image experiment was interrupted (exit 130), not accepted. Test-owned disposable
resources were removed after exact ownership checks; no user volumes/data changed.

Historical full acceptance (71 passing tests and nine passing CI jobs; old
vulnerability policy failed) is preserved in [PR16_ACCEPTANCE_HISTORY.md](PR16_ACCEPTANCE_HISTORY.md).
The current [known-risk register](KNOWN_SECURITY_ISSUES.md) retains all 181 distinct
advisory/package/version/severity rows across 12 images/13 services from verified
artifact 10290422302, not just high/critical findings. Raw reports remain unchanged.

Current work: small policy update, then shared connector interfaces and a real
generic JSON ingestion → normalized durable evidence → finding → webhook path.
No priority vendor integration is selected in the saved plan. Reference adapters
use local fixtures; no claim of live vendor validation or response enforcement.
Policy validation: `.venv/bin/pytest -o addopts= -q -ra`: 53 passed, 27
explicit integration/acceptance skips (those unchanged suites remain mandatory
in CI). `.venv/bin/python scripts/dependency_audit.py python --output
evidence/dependency-policy-python`: completed, zero known third-party findings;
unpublished editable package disclosed as unauditable. Compileall and diff checks
passed. Final GitHub/CI results will be recorded before handoff.

No schema, user credential, deployment, merge, tag or publication changes in the
policy slice. Existing backup/restore/rollback instructions remain applicable.
