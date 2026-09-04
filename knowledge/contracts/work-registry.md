# Work registry contract

`work/registry.json` is the machine-readable source of truth for coordination state. A human-readable `work/items/<id>.md` must exist for every registry entry.

## Required item fields

`id`, `title`, `level`, `status`, `owner`, `assigned_to`, `scope`, `depends_on`, `acceptance`, `files`, `evidence`, `reports`, `attempts`, `created_at`, `updated_at`.

## Invariants

- `id` matches `UA-####` and is unique.
- `level` is one of `L0` through `L4`.
- `status` is a known lifecycle state.
- `scope` and `acceptance` are non-empty arrays.
- Dependencies reference existing items and are acyclic.
- Active writer scopes do not overlap exact paths or parent/child subtrees.
- Recorded task files must be repository-relative and inside the task scope;
  malformed array fields are validation errors, not validator crashes.
- `done` requires non-empty review evidence with a repeatable command/result.
- `assigned` requires an agent mailbox and an assignment Markdown file.
- `reported` requires a worker report path from an already `in_progress` task; it
  is not equivalent to reviewed `done`.
- `reported` is written by `task report`; `task update --status reported` is
  rejected so a report-less completion cannot enter the registry.
- `needs_review` requires the task to already be `reported`; active workers
  cannot be reviewed or closed before their report is recorded.
- `done` and `cancelled` are terminal states; lifecycle updates cannot reopen or
  move them to another status.
- Review evidence and `needs_review`/`done` transitions require a registered
  `supervisor`, `reviewer` or `release_gate` identity; the assigned worker may
  not self-approve or self-close the task.
- Registered roles are limited to `supervisor`, `explorer`, `planner`, `worker`,
  `reviewer` and `release_gate`. Claim/report writers must use a non-review
  role; reviewers and release gates cannot claim implementation work.
- `assigned -> in_progress` is claim-only. `planned`, `blocked` and `cancelled`
  administrative updates require a registered review-capable identity; workers
  use `task report --result blocked` for a blocked handover.
- Direct `task claim` and `worker pull` must use an available claim-capable agent
  below `max_active` whose scope and capabilities satisfy the task; rejection
  occurs before registry mutation.
- Updates are serialized by `tools/useagent.py`; consumers must tolerate `updated_at` changing after every transition.
