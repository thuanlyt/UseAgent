# UseAgent audit

Independent read-only audit artifacts. The auditor was authorized to read the repository and write **only** inside this `audit/` directory.

## 2026-09-06 audit set

- [`FULL_AUDIT_2026-09-06.md`](FULL_AUDIT_2026-09-06.md) — repository architecture, security, correctness, concurrency, QA/production-gate, CI/test and maintainability review.
- [`COCKPIT_MULTI_AGENT_COMPARISON_2026-09-06.md`](COCKPIT_MULTI_AGENT_COMPARISON_2026-09-06.md) — UseAgent vs Cockpit Tools, how to combine them safely, and alternatives such as Herdr, OpenCode, Claude Managed Agents and Microsoft Agent Framework.

## Snapshot boundary

The code audit was performed against remote `main` at:

`0fd2244d68b8429213f0cbc6d7beaeb916f37620`

The user's Codex session was visibly in the middle of newer work when its usage quota was exhausted. Those local/unpushed changes are intentionally **not** treated as repository state in this audit. After Codex resumes and pushes a coherent checkpoint, run a delta audit against the new commit rather than blindly reapplying findings.

## Write-boundary statement

This audit did not modify application code, tests, configuration, documentation outside `audit/`, secrets, deployments, branches, issues, or release state. The only GitHub writes performed by the auditor are the audit documents in this directory.
