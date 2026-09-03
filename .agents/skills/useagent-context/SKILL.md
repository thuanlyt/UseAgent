---
name: useagent-context
description: "Build and refresh a compact, source-anchored project knowledge ledger so agents can find relevant context without rereading the whole repository."
---

# UseAgent Context

Use this skill when onboarding a repository, tracing an unfamiliar area, or updating durable project knowledge after a change.

1. Read `knowledge/INDEX.md` first. Use `python tools/useagent.py context --task <id>` for a bounded snapshot; include `work/SUPERVISOR_REPORT.md` when diagnosing the whole project.
2. Identify the smallest relevant module cards, contracts, decisions and source anchors. Inspect code only after this map points to likely files.
3. Write module cards around responsibility, entry points, interfaces, dependencies, invariants, tests and known gaps. Do not copy implementation or unverified assumptions.
4. When a public behavior or architectural choice changes, update the affected card and add/update a decision or contract with file/symbol anchors.
5. Record freshness and verification date. If the map is stale or contradictory, mark the gap and resolve it from the source before claiming the context is current.

Read [references/knowledge-model.md](references/knowledge-model.md) for the card format and freshness rules.
