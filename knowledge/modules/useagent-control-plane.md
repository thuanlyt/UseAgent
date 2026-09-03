# Module card: UseAgent control plane

- `freshness`: verified (2026-09-04)
- `owner`: orchestrator
- `source_anchor`: `tools/useagent.py:main`

## Responsibility

Create and transition work items, serialize state changes, print bounded context snapshots, create checkpoints and validate the repository coordination layer. It does not modify application code.

## Entry points

- `python tools/useagent.py context`
- `python tools/useagent.py task new|claim|update|evidence|report|list|show`
- `python tools/useagent.py agent register|status|list`
- `python tools/useagent.py worker pull --agent <id>`
- `python tools/useagent.py supervisor dispatch|ingest|report|qa|cycle`
- `python tools/useagent.py checkpoint create`
- `python tools/useagent.py validate`

## Public interfaces / contracts

See `knowledge/contracts/work-registry.md` and `knowledge/contracts/supervisor-protocol.md`. State lives in `work/registry.json`; item Markdown lives in `work/items/`. Repeated `--scope` options are preserved for a task, task scope can be extended through `task update`, and configured QA commands are shell command strings.

## Dependency edges

Consumes `AGENTS.md`, `knowledge/`, `work/` and `useagent.config.json`; is used by `$useagent` and all UseAgent skills/custom agents.

## Invariants

Lock only the short state transition. Do not hold the lock while doing exploration, implementation or tests. Reject overlapping active writer scopes and reject `done` without evidence.

## Verification

`python -m unittest discover -s tests -v`, `python tools/useagent.py validate`, configured supervisor QA and a temp-roster supervisor cycle.

## Known gaps

The scope checker understands path/subtree overlap, not arbitrary glob semantics. Git worktree orchestration remains a Codex/product operation rather than a hidden action of this CLI.
