# Repository guidance

- Preserve the four legacy workspaces and their routes while migrating callers
  to `src/agent_trust`.
- For code changes, run `pytest`, `python -m compileall -q src tests`, and the
  affected frontend build before committing. Documentation/developer-tooling-only
  changes need diff, link/render and applicable configuration checks; UI-copy-only
  changes need the affected frontend build/tests and report checks when affected.
- Runtime/storage changes require `pytest --run-integration tests/integration -v`
  against disposable Docker/PostgreSQL fixtures. A default pytest skip is not
  a passing runtime gate; never use operator data/volumes.
- Release/Compose changes also require `pytest --run-acceptance tests/acceptance -v`
  and `python3 scripts/scan_images.py`. Install the `acceptance` extra and
  Playwright Chromium first. See docs/ALPHA_ACCEPTANCE.md.
- Owner policy: known third-party dependency CVEs are accepted for development/
  alpha; hardening is deferred. Do not restart image/CVE remediation without an
  explicit request. Keep all findings, raw scans and SBOMs. Findings are
  informational; scanner execution/coverage failures remain blocking. Maintain
  docs/KNOWN_SECURITY_ISSUES.md. Never describe alpha as production-hardened.
- Keep build/runtime/functionality/migration/data-integrity and committed-secret
  gates. Approval is still required for merge/deployment/publication; never do
  those automatically. Continue the connector roadmap, not a hardening loop.
- Keep provider integrations optional and explicit. Missing credentials must
  produce unavailable/partial coverage, never synthetic success.
- Do not execute submitted source, MCP tools, OpenAPI operations, or untrusted
  model output. Keep workspace ownership server-bound.
- Use conventional commits, feature branches, and documented migration and
  rollback effects. Never commit `.env`, credentials, or generated artifacts.

## Least-cost model routing

- Optimize total engineering cost and first-pass correctness, not token cost or
  the cheapest first attempt. Include implementation time, failures, CI/debugging,
  rework, regressions, security risk and architectural churn. Choose the least
  expensive path with a high likelihood of a correct first implementation.
- Before delegation classify risk: LOW (narrow, reversible, deterministically
  verifiable) → shell/Luna/Terra-low; MEDIUM (bounded product behavior) →
  Terra-medium; HIGH (architecture/security/data integrity/protocol/concurrency
  or expensive rework) → Astra design, Terra implementation, tests, Astra review.
- Use shell commands first for authoritative deterministic evidence: Git, search,
  JSON/schema queries, inventories, checksums, tests, builds, lint/format and CI.
- Use `gpt-5.6-luna` / low for bounded low-risk inspection, log summaries,
  terminology/link review and basic status/PR drafts; prefer read-only work.
  Luna is an assistant, not the default implementation engineer. Do not assign
  work whose failure would require meaningful rewriting. Luna must not decide
  architecture, security, migrations or publication.
- Use `gpt-5.6-terra` for normal implementation, fixes, UI/backend work, tests,
  refactors, repository documentation and routine reviews. Use medium by default
  for nontrivial product code; low only for clearly mechanical work.
- Use `gpt-6-astra` / medium proactively before high-risk implementation, not just
  after failures; high only when justified. Require Astra design/review for auth,
  secrets, MCP execution/discovery/transports, network collectors/SSRF, isolation,
  migrations, queues/concurrency/fencing, endpoint privileges, enforcement,
  protocol compatibility and major cross-cutting architecture. Require final
  Astra review before merging these changes. Ordinary low/medium-risk changes
  use Terra review/tests plus bounded Astra acceptance before owner handoff.
  Release-readiness judgment also belongs to Astra.
- Workers may report IMPLEMENTATION COMPLETE, never self-declare TASK ACCEPTED.
  Before reporting any substantive repository task successfully completed to the
  owner, obtain independent Astra acceptance of the actual diff/implementation
  and verification evidence; worker summaries alone are not proof. Review depth
  is proportional to risk, including concise read-only review for docs/copy.
  High-risk work gets Astra before and after implementation. Failed acceptance
  returns a targeted remediation assignment to Terra, followed by checks and
  Astra review of the actual fix. Report the exact acceptance state and remaining
  limitations; never describe REJECTED or BLOCKED work as successfully complete.
- After one meaningful unexpected implementation failure, inspect deterministic
  evidence; fix directly if the cause is obvious, otherwise escalate reasoning
  or model quality. Do not burn repeated cheap attempts. Also escalate for
  genuine uncertainty, competing approaches, contradictory evidence or an explicit
  maximum-quality request. File count or nicer prose alone is not justification.
  Return implementation to Terra after the hard decision, then mechanical work
  to Luna or shell. Never substitute an unavailable model silently.
- Prefer explicit read-only `codex exec` workers with model/effort pinned and
  `agents.enabled=false`; native routing is not verified in the tested CLI.
  Parallelize only independent useful work, usually 2–4 workers, with narrow
  scope, output, write permission and verification stated. Avoid recursive trees.
- Never run parallel writers in one worktree; use isolated worktrees for parallel
  implementation. Give workers relevant files/diffs, acceptance criteria, concise
  failure evidence, security constraints and SHAs, not whole repositories/logs.
  Keep durable state in repository docs. Match verification to
  impact without weakening required runtime, security or release gates.

See [MODEL_ROUTING.md](docs/MODEL_ROUTING.md) for verified CLI commands, project
trust requirements, acceptance outcomes and routing limitations. Config defaults
do not switch an already-running session or override an explicit user model choice.
