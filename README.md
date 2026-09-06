# UseAgent

English | [Tiếng Việt](README-vi.md)

[![CI](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A file-first multi-agent control plane that turns one project goal into scoped work, inspectable handovers and bounded release progress.

UseAgent gives one capable model the role of supervisor. Other coding agents and humans join through the same repository-local protocol: shared context, explicit work items, mailboxes, evidence, review gates and checkpoints.

![UseAgent supervisor coordinating workers, reports and production gates](docs-site/assets/useagent-control-plane-hero.png)

## What UseAgent is

UseAgent is a provider-neutral supervisor workflow for trusted local agents working in one prepared repository. The supervisor reads a lightweight goal and roster, builds a roadmap/DAG, dispatches ready tasks, reviews worker reports, runs configured QA and chooses the next bounded action.

The repository is the shared memory:

```text
User goal
    ↓
UseAgent supervisor
    ├─ project brief, knowledge ledger and task DAG
    ├─ scoped assignments in worker mailboxes
    └─ reports, evidence, review, QA and checkpoints
    ↓
Codex · Claude Code · Antigravity · other workers · humans
    ↓
UseAgent supervisor → next safe action or an explicit blocker
```

The Python CLI owns deterministic state transitions and validation. The model owns planning, judgment and coordination. Markdown keeps handovers readable; JSON keeps the registry machine-checkable.

## Why teams use it

| Coordination problem | UseAgent response |
| --- | --- |
| Every agent rereads the repository | A compact, source-anchored `knowledge/` ledger |
| Work disappears in chat | A durable registry, assignment mailboxes and reports |
| Workers edit the same area | One active writer per path/subtree with scope checks |
| “Done” has no proof | Acceptance criteria, review evidence and repeatable checks |
| A long run loses direction | Bounded cycles, checkpoints and explicit stop conditions |
| QA or reports become stale | Provenance, report freshness and source-bound release evidence |

## Capabilities in the current release

### Plan and coordinate

- Supervisor front door through `$useagent`.
- Work levels from L0 discovery to L4 production/release.
- Dependency-aware task DAGs with scope, owner, capability and capacity checks.
- Per-agent `INBOX.md`, assignment inbox, `REPORT.md` and `COMPLETED.md`.
- Automatic dispatch to eligible workers; one writer owns a scope at a time.

### Preserve useful project memory

- Source-anchored knowledge cards and contracts that reduce rereading.
- Typed evidence provenance: `local`, `live`, `simulation`, `blocked`, `operator-confirmed` and compatible `legacy` history.
- Report freshness markers so `work/SUPERVISOR_REPORT.md` cannot silently look current when the registry moved on.
- First-class takeover lineage with `supersedes`, `superseded_by` and a preserved failure history.
- Bounded cycles and resumable checkpoints; no unbounded supervisor loop.

### Verify and release safely

- Sanitized, bounded durable summaries for runner and QA output.
- Local redacted diagnostic spool at `work/.runtime-output/`; raw runtime output is not repository evidence by default.
- Source-bound QA with Git HEAD, dirty-state, source-content and QA configuration fingerprints.
- Git release durability gate: clean release-relevant source, no non-ignored untracked release files and valid current QA.
- Structured QA `argv` execution with `shell=False` by default; shell syntax is an explicit trusted-local opt-in.
- Optional bounded worker runtime readiness and provider-neutral failure classification.
- Credential-free conformance coverage for Codex-, Claude Code- and Antigravity-style identities.
- No third-party Python runtime dependencies.

## Supported runtimes and roles

UseAgent does not require a particular model vendor. Codex, Claude Code, Google Antigravity, another compatible runtime or a human can work in the same repository when they can read the Markdown contract, run the CLI and respect the claimed scope.

Runtimes are execution surfaces; roles are workflow responsibilities:

| Role | Responsibility |
| --- | --- |
| `supervisor` | Understand the goal, plan the DAG, dispatch, review evidence, run QA and choose the next action |
| `explorer` | Read-only discovery, constraints and source anchors |
| `planner` | Decompose milestones into scoped work items |
| `worker` | Pull one assignment, implement within scope and report checks |
| `reviewer` | Inspect diff, regressions, security and evidence gaps |
| `release_gate` | Check acceptance, operations, rollback and release readiness |

The repository includes a practical [Codex + Claude Code + Antigravity onboarding guide](docs/getting-started.md). The conformance harness proves the shared protocol and routing; it does not claim that it called vendor APIs.

## Quick start

Requirements: Python 3.11+, Git, and a prepared project repository. UseAgent can live in the target repository or operate on an existing repository through `--root`.

```powershell
git clone https://github.com/thuanlyt/UseAgent.git
Set-Location UseAgent

python tools/useagent.py init
python tools/useagent.py validate
python examples/multi-agent-demo/run_demo.py
python examples/multi-runtime-conformance/run_conformance.py
```

For a separate prepared project:

```powershell
python F:\dev\UseAgent\tools\useagent.py --root F:\dev\MyProject init
python F:\dev\UseAgent\tools\useagent.py --root F:\dev\MyProject validate
```

`--root` comes before the subcommand. It makes the selected project the boundary for the registry, mailboxes, reports and configured paths. A configured path that escapes that boundary is rejected. See [getting started](docs/getting-started.md) for the copy-in and central-checkout choices.

Register the real worker sessions that will actually work on the project:

```powershell
python tools/useagent.py agent register `
  --id claude-frontend `
  --role worker `
  --scope src/frontend `
  --scope tests/frontend `
  --capability web `
  --max-active 1
```

Then give the supervisor a light prompt:

```text
Use $useagent in F:\dev\MyProject.
Goal: build a production-ready inventory API with authentication and tests.
Agents: codex-supervisor, claude-frontend, antigravity-reviewer.
Constraints: keep scopes non-overlapping; do not deploy or change secrets without approval.
Create the roadmap and scoped tasks, dispatch ready work, inspect reports, run QA,
review evidence and continue in bounded cycles until the release gate passes or I
need to decide a blocker.
```

The supervisor writes the full worker prompts to `work/outbox/`. Workers do not need a second hand-written assignment.

## The worker loop

The normal manual path is portable across runtimes:

```powershell
# supervisor: ingest reports, dispatch ready work and write the next checkpoint
python tools/useagent.py supervisor cycle

# worker: pull only after the supervisor assigned the task
python tools/useagent.py worker pull --agent claude-frontend

# worker: report the result through the CLI
python tools/useagent.py task report UA-0001 `
  --agent claude-frontend `
  --result completed `
  --summary "Frontend slice implemented and checked" `
  --next-action "Reviewer inspects the diff and accessibility evidence" `
  --file src/frontend/app.tsx `
  --check "npm test: pass"

# supervisor: ingest the report, review and run configured QA
python tools/useagent.py supervisor cycle --run-qa
python tools/useagent.py supervisor report --check
```

`reported` means that a worker submitted a handover. It is not `done`; a supervisor or reviewer must accept the evidence first. If a worker is blocked, it reports the concrete blocker instead of guessing or silently changing scope.

## Optional automatic worker intake

Automatic execution is opt-in. Configure a project-owned adapter as an argv list containing `{assignment_path}`:

```powershell
python tools/useagent.py agent register `
  --id codex-api `
  --role worker `
  --scope src/api `
  --scope tests/api `
  --capability python `
  --runner-arg=python `
  --runner-arg=tools/codex_worker_adapter.py `
  --runner-arg=--assignment `
  --runner-arg={assignment_path} `
  --runner-timeout 3600

python tools/useagent.py worker run --agent codex-api --max-tasks 1 --wait-seconds 300
```

The runner is bounded by task count, idle wait and timeout. An optional argv-only preflight can return an explicit `ready`, `unavailable`, `misconfigured`, `no_target` or `unknown` state before the task becomes `in_progress`. A missing report becomes a failed report; UseAgent does not retry forever or invent quota/auth facts from provider prose.

### Current QA configuration shape

QA commands are structured objects. The safe default passes literal arguments without a shell:

```json
{
  "supervisor": {
    "qa_timeout_seconds": 900,
    "qa_commands": [
      {
        "mode": "argv",
        "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
      }
    ]
  }
}
```

If shell composition is genuinely required, use an explicit `{ "mode": "shell", "command": "..." }` entry only in a trusted local repository. Shell mode is an execution capability, not a sandbox or authentication boundary. See [operations](docs/operations.md) for preflight, evidence, QA and release details.

## Autopilot and release integrity

One `supervisor cycle` is finite. It ingests reports, evaluates dependencies and review state, dispatches ready work, runs configured QA when requested and records a checkpoint. A scheduler may invoke another cycle later, but UseAgent does not create an infinite self-loop and never deploys by itself.

The release path keeps separate decisions separate:

1. A worker report says what was attempted.
2. Review accepts or rejects the work and evidence.
3. QA records bounded summaries and binds the result to the current source fingerprint.
4. The release durability gate checks Git HEAD, non-volatile cleanliness, untracked release files and QA validity.
5. Deployment remains an explicit operator-authorized action.

Generated control-plane state under the configured `release_source.volatile_paths` does not self-invalidate QA. Durable evidence contains sanitized summaries and provenance; detailed redacted diagnostics stay in the ignored `work/.runtime-output/` spool. Historical tracked evidence is preserved and is not automatically rewritten.

## Trust model and boundaries

UseAgent is designed for a **trusted-local / trusted-repository** threat model. Scope ownership is a workflow boundary, not an OS sandbox. The CLI cannot stop a non-compliant external process from writing outside its declared scope unless the project uses an additional isolation mechanism such as Git worktrees or CI-enforced diff checks.

UseAgent also does not authenticate agent identity, manage provider accounts or quotas, launch vendor APIs by guessing flags, or promise an autonomous infinite agent swarm. Stronger remote identity, sandboxing and provider integration belong in a project-owned adapter or execution environment.

## Real-world dogfood: OSBlog

UseAgent was dogfooded on OSBlog, a real open-source blog workload. The run covered multi-agent planning and dispatch, independent review/QA, Vercel release activity, worker quota interruption, checkpoint recovery, takeover lineage and human resume decisions. Those findings directly drove the UseAgent hardening shipped through UA-0048–UA-0055.

OSBlog is evidence for the control plane, not the product being documented here. Its live workload was Vercel-only; VPS, Netlify and local Node were documented targets, not claimed live environments. Read the [source-anchored case study](docs/case-study-osblog.md) and [capture manifest](docs/evidence/osblog-dogfood-capture-manifest.md) for the evidence boundary.

## Repository and documentation map

| Path | Purpose |
| --- | --- |
| `.agents/skills/` | Supervisor, context, orchestration, worker, review and bounded autopilot skills |
| `.codex/agents/` | Optional role-specific Codex profiles |
| `knowledge/` | Compact project brief, architecture, module cards, contracts and decisions |
| `work/` | Registry, assignments, reports, evidence and checkpoints |
| `tools/useagent.py` | Dependency-free state CLI and validator |
| `useagent.config.json` | Paths, roster, QA and production-readiness configuration |
| `docs/` | Hands-on, operations, autopilot and dogfood documentation |
| `docs-site/` | Crawlable bilingual static documentation site |
| `tests/` | Standard-library regression and docs-site tests |

Start with [getting started](docs/getting-started.md), then read [operations](docs/operations.md), [autopilot](docs/autopilot.md) and [architecture](docs/architecture.md). The public documentation site is at [useagent.thuanlyt.id.vn](https://useagent.thuanlyt.id.vn/).

## Contributing and license

Contributions follow the [work-item and review contract](CONTRIBUTING.md). For security reports, read [SECURITY.md](SECURITY.md). The project is released under the [MIT License](LICENSE).

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
