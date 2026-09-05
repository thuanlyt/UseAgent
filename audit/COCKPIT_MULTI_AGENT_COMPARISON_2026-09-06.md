# UseAgent vs Cockpit Tools — and practical multi-agent stacks

**Research date:** 2026-09-06  
**UseAgent snapshot used for comparison:** `0fd2244d68b8429213f0cbc6d7beaeb916f37620` (before this audit-only folder was added)

## Short answer

**UseAgent and Cockpit Tools are not direct competitors. They solve different layers and can be used together.**

- **Cockpit Tools** is primarily an **account / token / quota / local-instance operations layer** for many AI IDEs and coding tools.
- **UseAgent** is a **project work-control layer**: task DAG, scope ownership, agent mailboxes, evidence, review, QA, checkpoints and production gates.

For a user running several Codex / Claude / Antigravity-style workers, a strong pattern is:

```text
Cockpit Tools (accounts, quota, isolated app instances)
              ↓
optional Herdr (persistent terminal/session runtime)
              ↓
UseAgent (project ledger, task ownership, evidence, review/QA)
              ↓
Git worktree / sandbox per active writer
              ↓
Git + CI / release process
```

This composition is more complete than expecting any one of those tools to do every layer.

## What Cockpit Tools actually does

The vnROM article positions Cockpit Tools as a centralized dashboard for AI IDE accounts, tokens, quota and multiple sessions/instances. The current upstream repository similarly describes it as a universal AI IDE account manager with multi-account switching, quota monitoring, wake-up automation and parallel multi-instance management across many supported tools.

Sources:

- vnROM overview: https://vnrom.net/2026/04/cockpit-tools-cong-cu-quan-ly-tai-khoan-ai-ide-giup-chuyen-doi-nhieu-tai-khoan/
- upstream: https://github.com/jlcodes99/cockpit-tools

Operationally, this means Cockpit Tools sits **below** project orchestration. It knows which accounts/instances exist and how their local credential/config state is arranged. It does not replace a durable task graph, code-scope ownership protocol, reviewer gate, or project-specific QA ledger.

## Side-by-side comparison

| Capability | UseAgent | Cockpit Tools |
|---|---|---|
| Primary job | Coordinate work toward a project/release goal | Operate many AI IDE accounts and instances |
| Multi-account switching | No | Yes, core feature |
| Quota/usage dashboard | No | Yes, core feature |
| Multi-instance app launch | Not the focus; external workers are registered | Yes for supported tools/platforms |
| Task DAG / dependencies | Yes | No project-level DAG focus |
| One-writer scope ownership | Yes, ledger-level | No equivalent project ownership contract |
| Worker inbox/report protocol | Yes | No |
| Evidence / review lifecycle | Yes | No |
| QA / release gate | Yes | No project-specific release gate |
| Persistent checkpoints | Yes | Not the same project ledger concept |
| Vendor neutrality | Protocol works with many local runtimes | Broad AI IDE/account support, but adapters are product-specific |
| Filesystem isolation | Policy/coordination only unless paired with worktrees/sandbox | Per-instance profile/data isolation for supported app instances; not a code-scope sandbox |
| Credential handling | Intentionally does not grant credential authority | Directly works around local account/token/config state |
| Best fit | Multi-agent software project governance | Multi-account / quota / instance operations |

## Can they be “kẹp chung”? Yes — recommended mapping

### Pattern A — Cockpit + UseAgent

Best for a desktop developer who already uses Codex/Antigravity and has legitimate multiple accounts or separate work/personal/test identities.

1. Cockpit launches/maintains separate AI tool instances.
2. Give every running instance a stable UseAgent ID, for example:
   - `codex-primary`
   - `codex-reviewer`
   - `antigravity-frontend`
   - `claude-security`
3. Register each UseAgent agent with only the project scopes/capabilities it should own.
4. Prefer a **Git worktree per active writer**, even when Cockpit provides app-profile isolation. App-profile isolation is not the same as source-tree isolation.
5. Let UseAgent dispatch tasks and own the project ledger; do not make Cockpit account-switch state the source of truth for task ownership.
6. Run review/QA only after reconciling the actual Git diff with the declared task scope.

### Pattern B — Cockpit + Herdr + UseAgent

Best when many CLI agents need to stay alive for hours or across disconnects.

- Cockpit: identity/quota/instance operations.
- Herdr: persistent terminal processes, pane status and agent-to-agent terminal control.
- UseAgent: durable project planning, assignment, evidence and release gates.

Herdr describes itself as a background runtime that owns agent terminals, keeps sessions alive, reports working/blocked/idle state, and can run existing tools such as Claude Code, Codex, Cursor and OpenCode without replacing them: https://github.com/herdrdev/herdr

This is currently the most naturally complementary three-layer stack found in the research.

### Pattern C — UseAgent + OpenCode

Best when you are willing to standardize much of the coding workflow inside one agent harness instead of maintaining many desktop IDE instances.

OpenCode supports reusable primary/subagent profiles with model/tool permissions, including read-only exploration and background child sessions:

- https://opencode.ai/v2/docs/agents
- https://opencode.ai/v2/docs/commands

UseAgent can remain the durable cross-session ledger/release protocol while OpenCode provides the actual primary/subagent runtime. For small projects, however, OpenCode's native subagent flow may already be sufficient and UseAgent can be optional overhead.

### Pattern D — Claude Managed Agents

Best for a product/platform team building a service rather than driving desktop coding apps.

Anthropic's Managed Agents multiagent orchestration provides a coordinator that delegates to agents with separate context threads. Agents can have distinct models, prompts, tools, MCP servers and skills while operating in a managed session environment:

- https://platform.claude.com/docs/en/managed-agents/multi-agent

This is an API/platform-level alternative. It solves runtime orchestration more directly than UseAgent, but it is a different deployment model and currently uses the Managed Agents beta surface. UseAgent's file-based ledger/audit pattern could still be useful around it when repository-local traceability is desired.

### Pattern E — Microsoft Agent Framework / enterprise multi-agent platform

Best for organizations building governed application agents rather than just coordinating local coding assistants.

Microsoft's current agent resources describe Microsoft Agent Framework as a unified open-source SDK for building agent and multi-agent systems, with workflow/human-intervention patterns and enterprise ecosystem integration:

- https://microsoft.github.io/agent-resources/microsoft-foundry/

This category is heavier than UseAgent/Cockpit and is appropriate when agents are part of a deployed application architecture.

## Important safety and operational caveats with Cockpit

### 1. Credential blast radius

Cockpit works close to OAuth tokens, JSON credentials and local application configuration. Treat it as privileged desktop software. Keep the machine and its local account protected, minimize who can access the profile directories, and do not copy raw credential files into UseAgent reports/evidence.

### 2. Do not use account rotation to evade provider rules

Multi-account support is operationally useful for legitimate separate identities, organizations, testing, or capacity that the provider permits. It should not be treated as a mechanism to bypass usage restrictions or provider Terms of Service.

### 3. Avoid global-account races

If two workers depend on one mutable global `~/.codex` or equivalent active-account state, switching the account while both are running can create nondeterministic behavior. Prefer Cockpit's isolated instances/profile directories where supported and bind one long-running worker to one instance identity for the duration of a task.

### 4. App isolation ≠ source isolation

Two Codex instances can still modify the same checkout. Use separate worktrees/containers or enforce diff ownership at review time.

### 5. License matters for teams

The current upstream Cockpit Tools repository states **CC BY-NC-SA 4.0 by default** and says commercial use — including enterprise internal commercial purposes — requires separate written commercial authorization. That makes it materially different from UseAgent's MIT license and Herdr's Apache-2.0 license.

Before a company adopts or redistributes Cockpit Tools, verify the current license in the upstream repository and obtain authorization if the planned use is commercial.

## Which option should a multi-agent user choose?

| User profile | Recommended stack | Why |
|---|---|---|
| One developer, several AI accounts/IDEs | **Cockpit + UseAgent + Git worktrees** | Account/quota convenience plus durable project control |
| Many CLI agents that must keep running | **Herdr + UseAgent**, add Cockpit if multi-account management is needed | Herdr owns terminals; UseAgent owns work/evidence |
| Wants one consolidated open coding harness | **OpenCode**, optionally UseAgent | Native primary/subagent model + permissions/background child sessions |
| Cross-vendor Codex/Claude/Antigravity project | **UseAgent + isolated runtime/worktree per agent**; Cockpit/Herdr as operations layers | UseAgent is vendor-neutral at the project protocol layer |
| Building SaaS/internal autonomous agent service | **Claude Managed Agents** or **Microsoft Agent Framework** | Managed/programmatic multiagent runtime rather than desktop-instance orchestration |
| Commercial company considering Cockpit | **License review first** | Current upstream default is non-commercial CC BY-NC-SA 4.0 |

## Product positioning recommendation for UseAgent

UseAgent should **not** try to become another Cockpit. That would drag credential storage, quota adapters, provider-specific account formats and desktop instance lifecycle into a project whose current advantage is being small, transparent and provider-neutral.

A stronger direction is to position UseAgent as the missing **project control plane** that can sit above Cockpit, Herdr, OpenCode, Codex, Claude Code, Antigravity and future runtimes.

Recommended integration contract:

```text
Runtime adapter capabilities
- identity: stable agent/runtime id
- availability: available/busy/offline
- spawn/pull: how to start or wake the runtime
- project_root/worktree: exact source tree it owns
- task_id: active UseAgent assignment
- quota_hint: optional, read-only
- evidence callback: report path/status only; never raw credentials
```

Then build adapters rather than absorbing provider logic:

- `adapter-cockpit`: instance/account availability metadata, no token ingestion
- `adapter-herdr`: pane/session lifecycle and status
- `adapter-opencode`: launch a named agent/command
- direct/manual adapter: existing Markdown + CLI protocol

This would let UseAgent stay a durable supervisor while other tools specialize in runtime/session/account operations.

## Recommendation for the current UseAgent project

**Best immediate route:** keep UseAgent independent, document Cockpit and Herdr as optional companion layers, and implement a small adapter interface only after the security findings in `FULL_AUDIT_2026-09-06.md` are addressed.

For the user's current workflow, the preferred topology is:

```text
Cockpit (optional account/quota + isolated Codex/Antigravity instances)
  + Herdr (optional persistent CLI sessions)
  + UseAgent supervisor
  + one Git worktree per writer
  + independent reviewer/QA
```

That topology gives each tool one clear responsibility and reduces the chance that account switching, task ownership, source isolation and release evidence become tangled in the same component.
