# Module card: UseAgent control plane

- `freshness`: verified (2026-09-06)
- `owner`: orchestrator
- `source_anchor`: `tools/useagent.py:default_root`, `tools/useagent.py:configure_root`, `tools/useagent.py:validate_relative_scope`, `tools/useagent.py:scope_overlaps`, `tools/useagent.py:scope_within`, `tools/useagent.py:append_markdown`, `tools/useagent.py:agent_claim_blocker`, `tools/useagent.py:cmd_task_new`, `tools/useagent.py:cmd_task_claim`, `tools/useagent.py:cmd_task_update`, `tools/useagent.py:cmd_task_report`, `tools/useagent.py:cmd_worker_pull`, `tools/useagent.py:ingest_reports_locked`, `tools/useagent.py:choose_next_action`, `tools/useagent.py:normalize_evidence_provenance`, `tools/useagent.py:normalize_evidence_source`, `tools/useagent.py:parse_evidence`, `tools/useagent.py:registry_revision`, `tools/useagent.py:release_source_fingerprint`, `tools/useagent.py:validate_qa_source`, `tools/useagent.py:supervisor_report_freshness`, `tools/useagent.py:build_supervisor_report`, `tools/useagent.py:cmd_supervisor_report`, `tools/useagent.py:cmd_context`, `tools/useagent.py:validate_registry`, `tools/useagent.py:main`, `tools/useagent.py:production_snapshot`, `tools/useagent.py:run_qa`

## Responsibility

Create and transition work items, serialize state changes, print bounded context snapshots, create checkpoints and validate the repository coordination layer. It does not modify application code.

## Entry points

- `python tools/useagent.py context`
- `python tools/useagent.py --root <project-root> context`
- `useagent context` after `python -m pip install --no-deps .`
- `python tools/useagent.py task new|claim|update|evidence|report|list|show`
- `python tools/useagent.py agent register|status|list`
- `python tools/useagent.py worker pull --agent <id>`
- `python tools/useagent.py worker run --agent <id> [--max-tasks N]`
- `python tools/useagent.py supervisor dispatch|ingest|report|qa|cycle`
- `python tools/useagent.py checkpoint create`
- `python tools/useagent.py validate`
- `python examples/multi-runtime-conformance/run_conformance.py`

## Public interfaces / contracts

See `knowledge/contracts/work-registry.md` and `knowledge/contracts/supervisor-protocol.md`. State lives in `work/registry.json`; item Markdown lives in `work/items/`. Repeated `--scope` options are preserved for a task, task scope can be extended through `task update`, takeover lineage is written by `task new --supersedes ... --takeover-reason ...`, configured QA commands are shell command strings, and production readiness files are repository-safe. A central checkout may pass `--root <project-root>` before the subcommand; all runtime globals and configured paths are rebound to that existing directory, and escape paths are rejected. Direct claims and pulls share dispatcher eligibility checks for availability, capacity, scope and capabilities.

The package entry point is `tools.useagent:main`; an installed CLI uses the
current working directory when the package is outside a prepared source
checkout. Markdown append operations preserve block separation without adding
blank lines at end of file.

Supervisor next-action selection prioritizes `blocked`, failed QA, failed
reports, `reported` work and then `needs_review` work before planned work or a
new task. This keeps a review gate from being hidden by unrelated planning.

Generated supervisor reports carry a deterministic SHA-256 revision of the
registry snapshot. `supervisor report --check` returns `fresh` only when that
marker matches the current registry; missing or malformed markers are
`unknown`, and stale/missing reports are never treated as current. Context
includes the report freshness label and warning. The registry and task evidence
remain authoritative.

Runner and QA output is runtime data first. Future writes keep only bounded
sanitized summaries in `work/evidence/`; bounded redacted diagnostics go to
the Git-ignored `work/.runtime-output/` spool. Historical tracked evidence is
preserved and requires an explicit migration policy before cleanup. Successful
QA binds its pass to a deterministic release-source fingerprint; stale or
missing fingerprints fail the production snapshot until QA is rerun. Volatile
control-plane roots are configured explicitly in `release_source.volatile_paths`
and excluded from the source manifest. The production snapshot separately
 evaluates `release_source_durability`: Git `HEAD`, clean nonvolatile tracked
 state, no non-ignored untracked release source and valid current QA are
 required for `pass`. QA can remain valid on a dirty development tree while
 durability fails. Branch/upstream/ahead-behind metadata is read locally and
never requires `origin/main`, a network push or a merge; non-Git projects are
explicitly `filesystem`/`manual` degraded mode.
The generated root convenience report `work/SUPERVISOR_REPORT.md` is also
configured as volatile so report refreshes cannot self-invalidate QA.

## Dependency edges

Consumes `AGENTS.md`, `knowledge/`, `work/` and `useagent.config.json`; is used by `$useagent` and all UseAgent skills/custom agents.

## Invariants

Lock only the short state transition. Do not hold the lock while doing exploration, implementation or tests. Reject claim bypasses from `assigned` to `in_progress`, unavailable or over-capacity direct claims/pulls, scope/capability-ineligible claims, claims or lifecycle reopening of superseded predecessors, unactivated worker reports, unauthorized administrative transitions, report-less `reported` transitions, review of active unreported work, lifecycle updates to terminal states, invalid roster roles, review-only agents claiming/reporting implementation work, overlapping active writer scopes, unsafe/out-of-scope recorded files, review actions from non-review roles and `done` without non-empty review evidence. Keep the selected project root explicit, validate malformed config/registry shapes without traceback, ignore unreadable/escaping reports safely and reject configured paths outside it.

## Verification

`python -m unittest discover -s tests -v`, `python tools/useagent.py validate`, `python examples/multi-runtime-conformance/run_conformance.py`, explicit-root CLI tests, package metadata/wheel smoke test, configured supervisor QA and a temp-roster supervisor cycle.

## Operator onboarding

`docs/getting-started.md` is the public hands-on guide. It defines the portable
runtime boundary: Codex, Claude Code and Google Antigravity are execution
surfaces, while `supervisor`, `worker`, `reviewer` and the other names are
workflow roles. It also documents the shared-folder default, the worktree
ledger caveat, unique runtime ids, generated outbox prompts and the exact
pull/report cycle.

## Optional execution bridge

`agent register --runner-arg ...` can persist an argv-only adapter for a real
worker runtime. `worker run` pulls assigned work, substitutes the assignment,
task and agent placeholders, invokes the adapter with a timeout and records
runner evidence. It never uses a shell, has a one-task default and generates a
failed worker report when the adapter omits `task report`. The adapter remains
provider-specific and trusted; UseAgent does not promise to sandbox an external
model process.

## Known gaps

Scopes use explicit repository-relative path/subtree semantics; arbitrary glob
patterns are intentionally not interpreted. Git worktree orchestration remains
a Codex/product operation rather than a hidden action of this CLI. Vendor
launch flags and hosted-runtime authentication remain outside the portable core
and belong in a project-owned adapter.
