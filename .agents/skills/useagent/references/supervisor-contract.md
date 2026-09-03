# UseAgent supervisor contract

## Startup from a light prompt

Collect the goal, constraints, workspace and agent roster from the user message. Inspect the repository map and existing state. If the stack is not established, propose the smallest production-suitable stack supported by the repository and available agents, then record the assumption in `knowledge/decisions/`.

## Cycle order

```text
read state -> analyze reports -> review completed work -> choose next outcome
-> create/validate DAG -> dispatch mailboxes -> delegate workers
-> inspect evidence -> run tests/QA -> create debug tasks if needed
-> update knowledge/report -> checkpoint -> next action
```

Run one bounded cycle at a time. Do not make a scheduled task an unbounded loop.

## Reports

Read the full report Markdown only for tasks in `reported`, `needs_review`, `blocked`, or for a production gate. Keep raw logs under `work/evidence/`; return concise conclusions with paths and commands.

## Completion policy

Worker `completed` is a claim, not a release decision. A task is `done` only after acceptance, evidence and review. A project is production-ready only after all milestone gates and operational/rollback requirements pass. Deployment remains a separate authorized action.

## User-facing output

Return: current health, what changed, report/evidence paths, blockers, assignments waiting for workers, QA/review result, and one next action. The canonical Markdown copy is `work/SUPERVISOR_REPORT.md`.
