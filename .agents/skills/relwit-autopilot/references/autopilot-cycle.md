# Autopilot cycle contract

## Inputs

Goal/completion criteria, latest checkpoint, compact knowledge index, ready work items and current permission boundary.

## One cycle

1. Select one outcome and at most the amount of work that can be verified this run.
2. Run `relwit supervisor cycle`; it ingests report `.md` files and dispatches ready scopes into worker mailboxes.
3. Workers run `relwit worker pull --agent <id>` and finish with `task report`, which updates the report/completed Markdown files.
4. Implement, verify and review.
5. Update registry, evidence and knowledge.
6. Write a checkpoint with one next action.

If telemetry is available, include its bounded Usage summary in the handover:
measured wall time, aggregate worker runtime, actual participants and explicit
authoritative/partial/unavailable token status. Never estimate tokens or copy
raw telemetry/runtime output into the handover.

## Terminal states

- `complete`: outcome and verification are genuinely satisfied.
- `blocked`: the same external/permission/dependency blocker has no safe workaround.
- `needs_input`: a user decision or authorization is required.

Never turn `blocked` or `needs_input` into a retry loop. A future scheduled run may resume only after the relevant state changes.
