---
name: useagent-autopilot
description: "Run one bounded, checkpointed cycle of long-running UseAgent work toward a production outcome, with explicit stop conditions and no implicit deploy authority."
---

# UseAgent Autopilot

Use this skill when continuing a multi-milestone project, resuming after interruption, or preparing a scheduled local-project workflow.

1. Read `AGENTS.md`, `knowledge/INDEX.md`, `work/SUPERVISOR_REPORT.md`, the newest checkpoint and `work/registry.json`.
2. Define this cycle's single safe outcome. Run `python tools/useagent.py supervisor cycle` to ingest reports, inspect status, dispatch only ready work whose dependencies are complete and whose writer scope is free, and emit a new report/checkpoint.
3. Use the orchestrator/worker/review skills as needed. Parallelize discovery and verification; serialize overlapping writes.
4. Require evidence for completed tasks and refresh affected knowledge. Never hide a blocker by marking work done.
5. If the cycle was not run through the CLI, create a checkpoint with `python tools/useagent.py checkpoint create ...` containing summary, evidence, blockers and exactly one next action. Keep `work/SUPERVISOR_REPORT.md` as the user-facing status surface.
6. Finish with `complete`, `blocked` or `needs_input`. Stop on ambiguity, missing access, repeated failure, scope conflict or any unapproved external/destructive action.

This skill can prepare the prompt for a scheduled task, but scheduling, permissions and deployment remain product/user-controlled actions. Read [references/autopilot-cycle.md](references/autopilot-cycle.md) for the cycle contract.
