---
name: useagent-worker
description: "Implement one assigned UseAgent work item with an explicit scope, focused verification, and a concise evidence-backed handover."
---

# UseAgent Worker

Use this skill when an orchestrator has assigned a concrete work item and the agent is allowed to edit its declared scope.

1. Read `AGENTS.md`, the task item, the compact context snapshot, and its acceptance criteria.
2. Pull the oldest assignment with `python tools/useagent.py worker pull --agent <agent-id>`. If the task was handed to you directly, claim it with `python tools/useagent.py task claim <id> --agent <agent-id>`. Do not edit before a successful claim/pull.
3. Explore only the relevant paths, make the smallest coherent change, and keep all edits inside the claimed scope. Create a follow-up task for newly discovered work.
4. Run focused tests or checks. Record changed files and repeatable evidence with `task evidence`.
5. Run `python tools/useagent.py task report <id> --agent <agent-id> --result completed ...` so the mailbox `REPORT.md`, central report inbox and `COMPLETED.md` are updated automatically. The supervisor/reviewer will move the item through `needs_review` and `done`; do not skip that gate.

Read [references/work-item.md](references/work-item.md) for the worker checklist and transition rules.
