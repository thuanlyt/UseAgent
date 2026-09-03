---
name: useagent-review
description: "Review a UseAgent work item for correctness, regressions, security and test gaps, then record concise evidence without changing application code."
---

# UseAgent Review

Use this skill when implementation is ready for an independent verification pass or a milestone needs a release gate.

1. Read `AGENTS.md`, `work/SUPERVISOR_REPORT.md`, the work item, the relevant knowledge cards, the diff and existing evidence.
2. Verify behavior against acceptance criteria; prioritize correctness, security, data loss, compatibility and missing regression tests.
3. Run the smallest useful focused checks and capture exact commands/results. Do not fix while reviewing; create a follow-up task for code changes.
4. Report each finding with severity, file/line, impact and reproduction. State explicitly when no actionable finding was found.
5. Store long output under `work/evidence/`, add a short registry evidence entry, update the worker report if needed, and recommend `done`, `blocked` or another iteration.

Read [references/review-gate.md](references/review-gate.md) for the review rubric and release gate.
