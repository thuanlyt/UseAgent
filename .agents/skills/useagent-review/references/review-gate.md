# Review and release gate

## Priority order

1. P0 — data loss, security compromise, production outage or unsafe release.
2. P1 — broken acceptance behavior, serious regression or incompatible contract.
3. P2 — missing important regression coverage, error handling or operational evidence.
4. P3 — maintainability issue that is actionable but not release-blocking.

Do not report style-only observations unless they conceal a correctness or operational risk.

## Finding format

`[P1] path/to/file:line — impact; reproduction/why; proposed follow-up task.`

## Gate checklist

- Acceptance criteria are all evidenced.
- Focused tests pass and relevant regression coverage exists.
- Changed contracts and module cards are current.
- No unresolved P0/P1 finding.
- Operational/rollback notes exist for L3/L4 work.
- Any deploy or external mutation is explicitly authorized outside this skill.
