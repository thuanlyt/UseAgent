---
name: useagent-orchestrator
description: "Decompose a project goal into scoped UseAgent work items, coordinate specialized agents, and consolidate evidence at safe gates."
---

# UseAgent Orchestrator

Use this skill when the request spans multiple files, modules, agents, milestones, or a long-running production outcome.

1. Read `AGENTS.md`, `knowledge/INDEX.md`, the relevant architecture/module cards, and `work/registry.json`.
2. Classify the request as L0-L4 and define the completion gate before assigning work.
3. Split the goal into work items with narrow `scope`, explicit acceptance criteria, dependencies, owner and verification command. Create them with `python tools/useagent.py task new ...`.
4. Register the real worker roster once with `python tools/useagent.py agent register ...`, then run `python tools/useagent.py supervisor dispatch` or the full `supervisor cycle`. This emits an assignment `.md` into each eligible agent mailbox and a copyable prompt in `work/outbox/`.
5. Delegate independent read-heavy discovery in parallel. Delegate write work only when scopes are disjoint; otherwise create dependencies or use isolated Git worktrees.
6. Keep the parent thread on decisions and summaries. Ask agents to pull their mailbox task and return paths, symbols, commands, evidence and blockers rather than raw logs.
7. Require a reviewer or release gate before a milestone is accepted. Update module cards/contracts/decisions when behavior or architecture changed.
8. End each orchestration cycle with `python tools/useagent.py checkpoint create ...` or let `supervisor cycle` create one. Stop for ambiguity, missing access, scope conflict, repeated failure, or an unapproved external/destructive action.

Read [references/orchestration.md](references/orchestration.md) for level selection, DAG shape and handover format.
