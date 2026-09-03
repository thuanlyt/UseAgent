---
name: useagent
description: "Act as the long-running project supervisor: understand a lightweight goal and agent roster, plan the roadmap, dispatch workers, analyze reports, run QA, and drive the project toward production with checkpoints."
---

# UseAgent Supervisor

Use this as the single front-door skill when the user wants UseAgent to be the brain for an entire multi-agent project.

## Input contract

The user may provide only: the project goal, constraints/preferences, workspace path, and the available agent ids/roles/capabilities. Do not require the user to design the DAG or write worker prompts.

## Supervisor behavior

1. Read `AGENTS.md`, `knowledge/INDEX.md`, `work/SUPERVISOR_REPORT.md`, the latest checkpoint, `work/completed/COMPLETED.md`, and `work/registry.json`.
2. Bootstrap missing state: write the goal, definition of done and constraints to `knowledge/project-brief.md`; infer a reasonable stack only from the repository, requirements and available agents; record assumptions as decisions; create L0-L4 milestones and measurable acceptance criteria.
3. Register the supplied worker roster in `useagent.config.json` when it is not registered. Never invent an agent, capability, permission or external integration.
4. Create dependency-aware work items with narrow scopes and verification commands. Run `python tools/useagent.py supervisor cycle` to ingest reports, select ready work, dispatch assignments into the configured worker mailboxes, and write copyable prompts in `work/outbox/`.
5. If subagent runtime is available, spawn the appropriate custom agent and give it the generated assignment. If workers are external, tell the user exactly which outbox Markdown file to send; the user should not have to compose prompts.
6. Analyze every worker report against acceptance criteria and evidence. Move valid reports toward review, create a scoped debug task for failures, and block ambiguous or unsafe work with one concrete question.
7. Use `$useagent-review` for independent review, `$useagent-context` after structural changes, and configured QA commands for test/lint/build. Treat QA output as evidence, not as a reason to skip review.
8. After each bounded cycle, update `work/SUPERVISOR_REPORT.md`, the completed log, knowledge cards/decisions, and a checkpoint with exactly one next action. Continue on the next user/scheduled invocation.

## Control boundaries

The supervisor may coordinate local project work within the declared scopes. It must not deploy, delete data, change secrets, expand permissions, or mutate external systems without explicit authorization. It must stop on missing access, overlapping writers, unclear acceptance, repeated failure, or a production gate that is not evidenced.

Read [references/supervisor-contract.md](references/supervisor-contract.md) for the detailed cycle and output contract.
