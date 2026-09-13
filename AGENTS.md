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

- Use shell commands first for deterministic facts: Git, search, JSON queries,
  checksums, tests, builds, lint/format, links and CI status.
- Use `gpt-5.6-luna` / low for bounded low-risk inspection, log summaries,
  terminology/link review and basic status/PR drafts; prefer read-only work.
  Luna must not decide architecture, security, migrations or publication.
- Use `gpt-5.6-terra` for normal implementation, fixes, UI/backend work, tests,
  refactors, repository documentation and routine reviews; low for straightforward
  tasks, medium for normal engineering. This is the day-to-day default.
- Use `gpt-6-astra` / medium selectively for difficult architecture/security,
  authorization, concurrency, migrations/data integrity, contradictory evidence
  and final security-sensitive merge/release review; high only when justified.
- Escalate for genuine uncertainty, high impact, architectural choices, repeated
  failures, cross-subsystem behavior, final merge/release judgment or an explicit
  maximum-quality request. File count or nicer prose alone is not justification.
  Return implementation to Terra after the hard decision, then mechanical work
  to Luna or shell. Never substitute an unavailable model silently.
- Prefer explicit read-only `codex exec` workers with model/effort pinned and
  `agents.enabled=false`; native routing is not verified in the tested CLI.
  Parallelize only independent useful work, usually 2–4 workers, with narrow
  scope, output, write permission and verification stated. Avoid recursive trees.
- Never run parallel writers in one worktree; use isolated worktrees for parallel
  implementation. Give workers relevant ranges/summaries and SHAs, not whole
  repositories/logs. Keep durable state in repository docs. Match verification to
  impact without weakening required runtime, security or release gates.

See [MODEL_ROUTING.md](docs/MODEL_ROUTING.md) for verified CLI commands, project
trust requirements and routing limitations. Config defaults do not switch an
already-running session or override an explicit user model choice.
