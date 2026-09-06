---
type: useagent-assignment
task_id: UA-0057
agent: supervisor
created_at: 2026-09-06T18:27:36Z
scope: ["README-vi.md", "README.md", "docs-site/README.md", "docs-site/case-study.html", "docs-site/getting-started.html", "docs-site/operations.html", "docs-site/vi.html", "docs/autopilot.md", "docs/case-study-osblog.md", "docs/evidence/osblog-dogfood-capture-manifest.md", "docs/getting-started.md", "docs/operations.md"]
---

# Assignment UA-0057: Finalize bilingual README and documentation consistency

You are the assigned worker. Use `$useagent-worker` and do not modify files outside the scope below.

## Objective

Make README.md the canonical English product overview, create a complete Vietnamese counterpart, and reconcile public documentation with the current UseAgent release contracts without changing application architecture or reopening OSBlog work.

## Scope

- `README-vi.md`
- `README.md`
- `docs-site/README.md`
- `docs-site/case-study.html`
- `docs-site/getting-started.html`
- `docs-site/operations.html`
- `docs-site/vi.html`
- `docs/autopilot.md`
- `docs/case-study-osblog.md`
- `docs/evidence/osblog-dogfood-capture-manifest.md`
- `docs/getting-started.md`
- `docs/operations.md`

## Dependencies

- none

## Acceptance

- [ ] README.md is concise canonical English documentation with clear product positioning, current capabilities, trusted-local limitations, quick start, workflow, case study, support and license links.
- [ ] README-vi.md is a complete natural Vietnamese counterpart with matching structure, factual claims, limitations and language navigation.
- [ ] All README examples use the current structured QA and runtime contracts; no stale string qa_commands or sandbox/authentication claims remain.
- [ ] Public docs and docs-site references have no factual contradiction or broken navigation introduced by the split.

## Verification

- `python -m unittest tests.docs_site.test_docs_site -v`
- `python docs-site/build.py --check-only`
- `python tools/useagent.py validate`
- `git diff --check`

## Read first

- `AGENTS.md`
- `knowledge/INDEX.md`
- `work/items/UA-0057.md`

## Required report

Run `python tools/useagent.py task report UA-0057 --agent supervisor --result completed --summary "..." --next-action "Review"`.
Include changed files, checks/evidence and blockers. The supervisor will review before done.

## Assignment path

`work/agents/supervisor/inbox/UA-0057.md`
