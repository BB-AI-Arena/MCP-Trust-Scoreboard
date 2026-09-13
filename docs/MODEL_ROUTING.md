# Quality-gated cost routing

Optimize **first-pass correctness and total engineering cost**, not token cost
or the cheapest first attempt. Total cost includes model/API use, implementation
time, failed attempts, CI failures, debugging, rework, regressions, security risk
and architectural churn. Choose the least expensive execution path with a **high
likelihood of producing a correct first implementation**. Do not assign a weaker
model when a poor result would likely require significant rewriting.

**Shell → Luna → Terra → Astra** describes available tiers, not a mandatory
sequence of cheap attempts. Start high-risk work with Astra judgment. This is the
owner's routing policy, not a pricing guarantee; product behavior and publication
authority are unchanged.

| Tier | Model / effort | Work |
| --- | --- | --- |
| Shell | No model | Git/ref/diff inspection, rg/jq, counts/checksums, migration lists, tests/builds/compileall, lint/format, links and CI status. |
| Luna | `gpt-5.6-luna` / low | Assistant for bounded, preferably read-only inventories, log/CI summaries, straightforward failure classification, terminology/docs/link review, mechanical comparisons and existing-evidence summaries. Not the default implementation engineer; no architecture, security, migration or publication decisions. |
| Terra | `gpt-5.6-terra` / medium by default; low only for clearly mechanical work | Normal backend/frontend implementation, approved connector designs, fixtures/tests, bounded refactors, repository docs, straightforward fixes, PR preparation and routine reviews. |
| Astra | `gpt-6-astra` / medium; high when justified | Proactive high-risk architecture/security judgment before implementation and final review, difficult diagnosis, contradictory evidence and release-readiness decisions. Focus on judgment, not mechanical repository work. |

## Classify risk before delegation

| Risk | Scope | Execution path |
| --- | --- | --- |
| LOW | Narrow, reversible work with deterministic verification | Shell / Luna assistance / Terra-low for mechanical implementation. |
| MEDIUM | Bounded product behavior | Terra-medium implementation and review, plus applicable tests. |
| HIGH | Architecture, security, data integrity, protocol, concurrency or expensive rework | Astra designs/reviews the approach → Terra implements → deterministic tests → Astra final review. |

Require Astra involvement **before implementation** and **final Astra review
before merging** changes involving authentication/authorization, secret or
credential handling, MCP execution/discovery/transport boundaries, network
collectors/egress/SSRF, sandboxing/isolation, migrations/data integrity, durable
queues/concurrency/fencing, endpoint privileges/security controls, enforcement,
protocol compatibility design or major architecture/cross-cutting refactors.
Use Astra for release-readiness decisions as well. Ordinary low/medium-risk work
needs Terra review plus tests; it does not automatically need Astra.

After **one meaningful unexpected implementation failure**, inspect deterministic
evidence. Fix directly when the root cause is obvious; otherwise escalate reasoning
or model quality. Do not wait through several cheap attempts. Also escalate for
genuine uncertainty, competing approaches, contradictory evidence or an explicit
maximum-quality request. File count or polished prose alone is insufficient.

After Astra decides a direction, return implementation to Terra and mechanical
follow-up to Luna or shell. Review is a required quality gate where specified;
it never grants authority to merge, deploy, publish or execute live MCP tools.

## Project defaults and trust

[.codex/config.toml](../.codex/config.toml) selects Terra/medium with low verbosity.
It deliberately disables native agents; explicit worker processes remain available.
Global model, authentication, provider, sandbox and approval settings are unchanged.

Codex loads project config only for a trusted project, and explicit CLI/session
choices take precedence. Trust the exact Git root through your normal Codex setup
after reviewing its local configuration, hooks and rules. A linked worktree uses
the main checkout's Git-root trust entry. In the tested installation, broader
ancestor trust did **not** activate this repository's config. This change does not
write a global trust entry or claim that untrusted checkouts automatically use Terra.
A one-invocation `projects.<root>.trust_level` override also failed to activate
the project layer in the probe; do not rely on that shortcut for trust setup.
See [official configuration precedence and trust](https://developers.openai.com/codex/config-basic/).

Until project trust is configured, explicitly start normal engineering from the
checkout with:

```bash
codex --model gpt-5.6-terra \
  --config 'model_reasoning_effort="medium"' \
  --config 'model_verbosity="low"' \
  --config 'agents.enabled=false'
```

These defaults do not change an already-running session or a model explicitly
selected in an app. Confirm the selected model at session start. If a tier is
unavailable, report the limitation and justify any alternative; never silently
run the entire lifecycle on Astra.

## Explicit bounded workers

Run from the intended checkout, with a narrowly scoped task in place of the
example text. Existing Codex authentication is inherited; never copy credentials
into prompts, scripts, logs or repository files.

```bash
codex exec --strict-config --ephemeral \
  --model gpt-5.6-luna \
  --config 'model_reasoning_effort="low"' \
  --config 'agents.enabled=false' --sandbox read-only \
  'Read README.md only. List stale product names with line numbers. Do not change files or spawn workers. Return at most five bullets.'

codex exec --strict-config --ephemeral \
  --model gpt-6-astra \
  --config 'model_reasoning_effort="medium"' \
  --config 'agents.enabled=false' --sandbox read-only \
  'Review src/agent_trust/security/ only for credential-handling and egress risks. Do not change files or spawn workers. Return findings with evidence and uncertainty in at most five bullets.'
```

For a Terra worker, use the same pattern with `--model gpt-5.6-terra` and medium
effort; use low only for clearly mechanical work. Read-only is the default worker
policy. Grant workspace writes
only to an explicitly assigned implementer; never run independent writers in one
worktree. Use isolated Git worktrees when parallel implementation is useful.
Direct commands suffice; no wrapper scripts or automatic commits/pushes are added.

Usually use at most 2–4 workers, only for independent work that saves time/context.
Give each worker exact files/areas, expected output, write permission and required
verification. Do not recursively spawn trees without a clear difficult-task need.
Use shell or Luna to narrow evidence first. Give Terra/Astra relevant files and
diffs, acceptance criteria, concise failure evidence and security constraints.
Deterministic evidence is authoritative; avoid feeding entire logs/repositories
to expensive models. Return concise evidence, SHAs, filenames and uncertainty.

## Verification proportional to impact

- Documentation/tooling only: diff check, changed links/rendering and applicable
  configuration validation.
- UI copy: affected frontend build/tests; PDF/report validation if affected.
- Backend behavior: targeted tests plus repository-required unit/integration gates.
- Security/storage/migrations/releases: all applicable acceptance gates, including
  those in [AGENTS.md](../AGENTS.md). Do not weaken CI or repeat the release suite
  after low-risk edits without a new failure or unresolved concern.

## Installed CLI evidence and limitations

Checked on 2026-09-13 with **codex-cli 0.154.0**. Recheck after upgrades:

```bash
codex --version
codex exec --help
codex debug models --bundled | jq '.models[] | select(.slug == "gpt-5.6-luna" or .slug == "gpt-5.6-terra" or .slug == "gpt-6-astra") | {slug, default_reasoning_level, supported_reasoning_levels: [.supported_reasoning_levels[].effort]}'
```

The bundled catalog lists all three. Separate harmless explicit exec probes
returned the expected acknowledgement; CLI headers matched Terra/medium,
Luna/low and Astra/medium, with read-only sandbox and agents disabled. This verifies
CLI selection and successful service access, not independently attested backend
model identity or a capability benchmark.

TOML parsing and the installed app-server strict config parser accepted all
committed settings when supplied as explicit overrides, and `config/read`
returned Terra/medium, low verbosity and agents disabled. Reading the project
layer without persisted exact-root trust reported it disabled and retained the
global default. Automatic project-default activation is therefore not claimed
for this checkout; the explicit launch command above is the tested fallback.

An ephemeral native-spawn probe failed with `collab spawn failed: no thread with
id`. Its project config was disabled by missing exact-root trust, so the parent
retained the global model. No child model/effort was verified. Use explicit exec
workers; do not assume inheritance or claim silent child-model substitution.
Before enabling native routing, verify actual child model/effort in the intended
CLI/app mode; only then consider Terra native defaults with effort matched to
task risk (medium normally, low for mechanical work) and a four-worker cap.
Luna is not configured as a native default.

`--strict-config` works with `codex exec` but is rejected by `codex debug` in this
version. Use exec/config readback to validate loaded defaults, not an unchecked
config file or a model's self-description. `--ephemeral` is supported and avoids
persisting worker session files; it does not promise zero temporary/runtime logs.
