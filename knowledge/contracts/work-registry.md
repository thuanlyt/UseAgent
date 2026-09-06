# Work registry contract

`work/registry.json` is the machine-readable source of truth for coordination state. A human-readable `work/items/<id>.md` must exist for every registry entry.

## Required item fields

`id`, `title`, `level`, `status`, `owner`, `assigned_to`, `scope`, `depends_on`, `acceptance`, `files`, `evidence`, `reports`, `attempts`, `created_at`, `updated_at`.

New task items may also carry `supersedes`, `superseded_by` and
`takeover_reason`. These optional fields are omitted by legacy items, but a
CLI-created item always initializes them so a takeover is explicit.

## Evidence provenance

New evidence entries written by the CLI include `kind`, `value`, a controlled
`provenance`, a single-line `source` anchor and `recorded_at`. The supported
provenance values are `local` (verified against the selected checkout or a
local command), `live` (observed on a named deployed endpoint),
`simulation` (replay/mock/generated demonstration), `blocked` (an attempted
check could not be completed) and `operator-confirmed` (a human-confirmed
external fact). `legacy` is reserved for older Markdown reports that predate
the field and is never a claim that the evidence is verified.

Provenance is a typed label, not authentication or review approval. A `live`
label still needs a repeatable source and review evidence. Existing evidence
without the optional fields remains readable and valid for backward
compatibility; malformed new fields are validation errors.

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
- A takeover may reference only a `blocked` or `cancelled` predecessor. The
  successor's `supersedes` and predecessor's `superseded_by` must point to each
  other, and `takeover_reason` must be non-empty and single-line.
- A task with `superseded_by` is preserved as failure history and cannot be
  claimed or moved back into the active lifecycle. Takeover creation never
  reopens or silently mutates the predecessor's status, reports or evidence.
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
