# Least-cost development routing

Use **Shell → Luna → Terra → Astra**, selecting the cheapest tier likely to
succeed. This is the owner's routing policy, not a pricing or billing guarantee.
It changes developer tooling only; product behavior and publication authority
are unchanged.

| Tier | Model / effort | Work |
| --- | --- | --- |
| Shell | No model | Git/ref/diff inspection, rg/jq, counts/checksums, migration lists, tests/builds/compileall, lint/format, links and CI status. |
| Luna | `gpt-5.6-luna` / low | Bounded read-only inventories, log/CI summaries, straightforward classification, terminology/docs/link review, acceptance checklists and draft status/PR text. No architecture, security, migration or publication decisions. |
| Terra | `gpt-5.6-terra` / low or medium | Normal implementation, bounded fixes, UI/backend work with clear contracts, fixtures/tests, refactors, repository docs, PR preparation and routine reviews. |
| Astra | `gpt-6-astra` / medium; high when justified | Architecture, threat modeling, authorization, concurrency/fencing/idempotency, data integrity/migrations, major MCP collector design, difficult diagnosis, cross-subsystem decisions, contradictory evidence and final security-sensitive merge/release review. |

Escalate only for genuine uncertainty, high security/data-integrity impact,
competing architectures, repeated failed attempts, behavior crossing subsystems,
final merge/release judgment, contradictory evidence or an explicit user request
for maximum-quality reasoning. Many files or more polished prose is insufficient.
After Astra recommends a direction, return implementation to Terra; move
mechanical follow-up to Luna or shell. Advisory review never authorizes merging,
deployment, publication or live MCP tool execution.

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
  'Review AGENTS.md and docs/MODEL_ROUTING.md only for contradictory authority boundaries. Do not change files or spawn workers. Return findings with evidence in at most five bullets.'
```

For a Terra worker, use the same pattern with `--model gpt-5.6-terra` and low or
medium effort. Read-only is the default worker policy. Grant workspace writes
only to an explicitly assigned implementer; never run independent writers in one
worktree. Use isolated Git worktrees when parallel implementation is useful.
Direct commands suffice; no wrapper scripts or automatic commits/pushes are added.

Usually use at most 2–4 workers, only for independent work that saves time/context.
Give each worker exact files/areas, expected output, write permission and required
verification. Do not recursively spawn trees without a clear difficult-task need.
Use rg/jq and relevant ranges first; summarize large logs before expensive review.
Return concise evidence, SHAs, filenames and uncertainty to the parent.

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
CLI/app mode; only then consider Terra/low native defaults and a four-worker cap.
Luna is not configured as a native default.

`--strict-config` works with `codex exec` but is rejected by `codex debug` in this
version. Use exec/config readback to validate loaded defaults, not an unchecked
config file or a model's self-description. `--ephemeral` is supported and avoids
persisting worker session files; it does not promise zero temporary/runtime logs.
