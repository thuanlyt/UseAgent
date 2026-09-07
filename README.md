# UseAgent

English | [Tiếng Việt](README-vi.md)

[![CI](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/thuanlyt/UseAgent?display_name=tag&sort=semver)](https://github.com/thuanlyt/UseAgent/releases/latest)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A repo-local evidence and release-assurance layer for AI coding workflows.
> Lightweight supervision is available when a project benefits from it.

![UseAgent release-assurance workflow for AI coding projects](docs-site/assets/useagent-control-plane-hero.webp)

## What UseAgent is

UseAgent keeps the proof around AI-assisted coding in the repository that is
being changed. It records evidence provenance, bounds and sanitizes durable
output, binds QA to a source snapshot, verifies review evidence and checks Git
release durability before a release decision.

The result is a compact, inspectable trail for the questions that matter:

- What changed, and which source state was checked?
- Which evidence is local, live, simulated or blocked?
- Did review and QA verify the same source that is ready to ship?
- Is the repository clean and durable enough for the next release gate?

UseAgent is provider-neutral and trusted-local. It complements the coding
runtime rather than trying to become one.

## Current Release

**v0.1.0 — Initial Public Release**

v0.1.0 is the current public release. The feature set is now frozen after the
release-assurance maintenance pass: future changes require a concrete bug,
security issue, real external-user evidence or an explicit owner decision.

- [Release notes](https://github.com/thuanlyt/UseAgent/releases/tag/v0.1.0) · [All releases](https://github.com/thuanlyt/UseAgent/releases)
- [CHANGELOG](CHANGELOG.md) · [Documentation](https://useagent.thuanlyt.id.vn/) · [Getting started](docs/getting-started.md)

The public repository does not ship a maintainer's runtime history. `work/`
is generated locally by `init` in the project being assured.

## Why teams use it

| Release-assurance problem | UseAgent response |
| --- | --- |
| AI output is hard to audit later | Typed evidence provenance and source-anchored handovers |
| A green check may belong to an older tree | Source-bound QA and explicit freshness checks |
| Raw runner output can contain secrets | Bounded sanitized summaries plus a local diagnostic spool |
| “Done” is confused with “ready to release” | Separate review, QA and Git durability gates |
| Long work loses its durable context | Compact knowledge cards, reports and checkpoints |
| Different coding runtimes use different workflows | One repository-local contract around their output |

## Why UseAgent if I already use Claude Code, Codex, Beads or worktrees?

Those tools plan and execute work. UseAgent verifies the evidence and release
state around the resulting repository. It can sit beside them without asking
them to surrender their native planning, subagents, branches or worktree
management:

```text
Claude Code / Codex / Beads / worktrees
        plan and execute
                ↓
UseAgent verifies evidence, source identity and release durability
```

UseAgent is a complement, not a replacement for Beads, Spec Kit, native Claude
or Codex subagents, Git worktree managers or a project's CI system.

## What it verifies

- Evidence is labeled with controlled provenance and repeatable source anchors.
- Durable runner and QA summaries are bounded and sanitized; raw diagnostics
  remain local by default.
- QA is bound to Git HEAD, source content, dirty-state provenance and QA
  configuration.
- Review evidence is required before a work item is considered done.
- Release durability checks the relevant Git cleanliness, untracked files and
  current QA validity separately from task completion.
- Configured quality gates remain explicit and deployment authority stays with
  the project owner.

## Optional lightweight supervision

When a project wants a supervisor, `$useagent` can turn a short goal into a
bounded workflow: record assumptions, create dependency-aware work items,
dispatch assignments, ingest reports, inspect evidence, run QA and checkpoint
the next action. The DAG, mailbox, role and telemetry machinery remains
available, but it is an optional coordination capability—not the product's
primary identity.

Workflow roles are personas, not vendor identities:

| Role | Responsibility |
| --- | --- |
| `supervisor` | Plan bounded work, review evidence and choose the next safe action |
| `explorer` | Read-only discovery and source anchors |
| `planner` | Decompose a goal into scoped work items |
| `worker` | Implement one claimed scope and report checks |
| `reviewer` | Verify diff, regressions, security and evidence |
| `release_gate` | Check release readiness and operational evidence |

Codex, Claude Code, Google Antigravity and other coding agents can be workers
when they can read the repository contract, run the CLI and respect scope.
See the [practical runtime guide](docs/getting-started.md).

## Judgment-aware supervision

The optional supervisor records the decision boundary, not a hidden chain of
thought. For each bounded cycle it should state the intent, tradeoff, owner,
evidence anchors and next action or stop condition. When the marginal value is
low or the evidence is ambiguous, it should stop and ask the owner instead of
creating more work. This keeps coordination useful while respecting
diminishing returns and the trusted-local boundary.

## Quick start for an external project

UseAgent is normally cloned or installed once, then pointed at the repository
you want to assure. Do not use the UseAgent source checkout as the default
application workspace.

Requirements: Python 3.11+, Git, and an existing target repository.

```powershell
git clone https://github.com/thuanlyt/UseAgent.git F:\tools\UseAgent
python F:\tools\UseAgent\tools\useagent.py --root F:\dev\MyProject init
```

`init` creates empty local state under `F:\dev\MyProject\work`. It does not
copy skills or overwrite project files. For the full workflow, copy or merge
the UseAgent control-plane files (`AGENTS.md`, `.agents/skills/`, `knowledge/`,
`tools/useagent.py` and configuration) into the target repository, preserving
the target project's own instructions and source. Then run:

```powershell
python F:\tools\UseAgent\tools\useagent.py --root F:\dev\MyProject validate
```

The `--root` boundary covers the registry, reports, evidence, checkpoints and
all configured paths. Paths that escape it are rejected. If the CLI has been
installed, the equivalent form is:

```powershell
python -m pip install --no-deps F:\tools\UseAgent
useagent --root F:\dev\MyProject init
useagent --root F:\dev\MyProject validate
```

Read [getting started](docs/getting-started.md) before registering workers.

## The assurance loop

The core path is useful with one agent or many:

```text
implement → report evidence → review → source-bound QA → Git durability gate
```

If supervision is enabled, the optional loop adds:

```powershell
python tools/useagent.py supervisor cycle --run-qa
python tools/useagent.py supervisor report --check
```

Workers can use the generated mailbox/report protocol, but a project may also
use UseAgent around work planned by an external orchestrator. A worker report
is not a release decision; the reviewer, QA and durability gates remain
separate.

## Trust model and concurrency boundary

UseAgent is designed for a **trusted-local / trusted-repository** threat model.
Its scope and role checks are workflow controls, not an OS sandbox, authenticated
distributed lock or authenticated agent identity system.

UseAgent does not own:

- branches, worktrees or parallel process isolation;
- provider accounts, quotas or vendor API launch flags;
- a project's task graph when another orchestrator already owns it;
- deployment or external mutations.

External orchestrators may manage branches, worktrees, parallel execution and
task graphs. UseAgent can verify the resulting repository state. The shared
folder and mailbox workflow documented in the optional supervision guide is
deliberately lightweight and trusted-local.

## Repository and documentation map

| Path | Purpose |
| --- | --- |
| `.agents/skills/` | Optional supervisor, context, worker, review and autopilot skills |
| `.codex/agents/` | Optional role-specific Codex profiles |
| `knowledge/` | Compact project brief, architecture, contracts and decisions |
| `tools/useagent.py` | Dependency-free assurance CLI and validator |
| `useagent.config.json` | Paths, QA and production-readiness configuration |
| `work/` | Generated local registry, reports, evidence and checkpoints after `init` |
| `docs/` | Canonical hands-on, operations, architecture and case-study docs |
| `docs-site/` | Crawlable bilingual static documentation site |
| `tests/` | Standard-library regression and docs-site tests |

The [OSBlog dogfooding case study](docs/case-study-osblog.md) shows how a real
workload used evidence, QA and recovery boundaries. OSBlog is a workload and
evidence source, not the product being positioned here.

## Packaging note

The current package intentionally keeps the stable public entry point
`useagent = tools.useagent:main` and `packages = ["tools"]`. The generic
top-level `tools` package can collide with another application's package when
both are imported in one Python environment, although the installed CLI and
wheel smoke path are usable. A namespace migration is a compatibility change
and is outside this frozen pass; it should only be reconsidered with concrete
install evidence and an explicit maintenance-release decision.

## Contributing and license

Contributions follow the [work-item and review contract](CONTRIBUTING.md). For
security reports, read [SECURITY.md](SECURITY.md). The project is released under
the [MIT License](LICENSE).

---

## 💖 Support the Project

UseAgent is **free and open source**. If it saves you time, please give us a ⭐ **Star** — it keeps the project alive and helps us ship more skills.

<a href="https://github.com/thuanlyt/UseAgent/stargazers">
  <img src="https://img.shields.io/github/stars/thuanlyt/UseAgent?style=social" alt="GitHub Stars">
</a>

### 🤝 Community & Support
- 📖 [Read the Docs](https://useagent.thuanlyt.id.vn/)
- 🐛 [Report an Issue](https://github.com/thuanlyt/UseAgent/issues)
- 🌐 [ThuanLYT Website](https://thuanlyt.id.vn)

<p align="center"><em>Built with ❤️ by ThuanLYT</em></p>
