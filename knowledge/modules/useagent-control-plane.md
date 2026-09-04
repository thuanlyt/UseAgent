# Module card: UseAgent control plane

- `freshness`: verified (2026-09-04)
- `owner`: orchestrator
- `source_anchor`: `tools/useagent.py:default_root`, `tools/useagent.py:configure_root`, `tools/useagent.py:validate_relative_scope`, `tools/useagent.py:scope_overlaps`, `tools/useagent.py:scope_within`, `tools/useagent.py:append_markdown`, `tools/useagent.py:choose_next_action`, `tools/useagent.py:main`, `tools/useagent.py:production_snapshot`, `tools/useagent.py:run_qa`

## Responsibility

Create and transition work items, serialize state changes, print bounded context snapshots, create checkpoints and validate the repository coordination layer. It does not modify application code.

## Entry points

- `python tools/useagent.py context`
- `python tools/useagent.py --root <project-root> context`
- `useagent context` after `python -m pip install --no-deps .`
- `python tools/useagent.py task new|claim|update|evidence|report|list|show`
- `python tools/useagent.py agent register|status|list`
- `python tools/useagent.py worker pull --agent <id>`
- `python tools/useagent.py supervisor dispatch|ingest|report|qa|cycle`
- `python tools/useagent.py checkpoint create`
- `python tools/useagent.py validate`
- `python examples/multi-runtime-conformance/run_conformance.py`

## Public interfaces / contracts

See `knowledge/contracts/work-registry.md` and `knowledge/contracts/supervisor-protocol.md`. State lives in `work/registry.json`; item Markdown lives in `work/items/`. Repeated `--scope` options are preserved for a task, task scope can be extended through `task update`, configured QA commands are shell command strings, and production readiness files are repository-safe. A central checkout may pass `--root <project-root>` before the subcommand; all runtime globals and configured paths are rebound to that existing directory, and escape paths are rejected.

The package entry point is `tools.useagent:main`; an installed CLI uses the
current working directory when the package is outside a prepared source
checkout. Markdown append operations preserve block separation without adding
blank lines at end of file.

Supervisor next-action selection prioritizes `blocked`, failed QA, failed
reports, `reported` work and then `needs_review` work before planned work or a
new task. This keeps a review gate from being hidden by unrelated planning.

## Dependency edges

Consumes `AGENTS.md`, `knowledge/`, `work/` and `useagent.config.json`; is used by `$useagent` and all UseAgent skills/custom agents.

## Invariants

Lock only the short state transition. Do not hold the lock while doing exploration, implementation or tests. Reject report-less `reported` transitions, overlapping active writer scopes, unsafe/out-of-scope recorded files, review actions from non-review roles and `done` without non-empty review evidence. Keep the selected project root explicit, validate malformed config/registry shapes without traceback, ignore unreadable/escaping reports safely and reject configured paths outside it.

## Verification

`python -m unittest discover -s tests -v`, `python tools/useagent.py validate`, `python examples/multi-runtime-conformance/run_conformance.py`, explicit-root CLI tests, package metadata/wheel smoke test, configured supervisor QA and a temp-roster supervisor cycle.

## Operator onboarding

`docs/getting-started.md` is the public hands-on guide. It defines the portable
runtime boundary: Codex, Claude Code and Google Antigravity are execution
surfaces, while `supervisor`, `worker`, `reviewer` and the other names are
workflow roles. It also documents the shared-folder default, the worktree
ledger caveat, unique runtime ids, generated outbox prompts and the exact
pull/report cycle.

## Known gaps

Scopes use explicit repository-relative path/subtree semantics; arbitrary glob
patterns are intentionally not interpreted. Git worktree orchestration remains
a Codex/product operation rather than a hidden action of this CLI.
