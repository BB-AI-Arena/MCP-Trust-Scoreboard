# Repository guidance

- Preserve the four legacy workspaces and their routes while migrating callers
  to `src/agent_trust`.
- Run `pytest`, `python -m compileall -q src tests`, and the affected frontend
  build before committing.
- Keep provider integrations optional and explicit. Missing credentials must
  produce unavailable/partial coverage, never synthetic success.
- Do not execute submitted source, MCP tools, OpenAPI operations, or untrusted
  model output. Keep workspace ownership server-bound.
- Use conventional commits, feature branches, and documented migration and
  rollback effects. Never commit `.env`, credentials, or generated artifacts.
