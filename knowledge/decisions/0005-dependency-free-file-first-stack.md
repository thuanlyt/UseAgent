# ADR-0005: Dependency-free file-first control-plane stack

- **Status:** accepted
- **Date:** 2026-09-04
- **Owner:** supervisor

## Context

UseAgent must be portable across repositories and agent runtimes, recoverable after a stopped session, and cheap to understand without installing a service or rereading the whole codebase.

## Decision

Use Python 3.11+ standard library for the control-plane CLI and tests, JSON for machine state/configuration, Markdown for knowledge/work/mailboxes/reports, TOML for optional Codex agent profiles, and GitHub Actions for repeatable CI. Keep runtime paths repository-relative and make external execution explicit through configured QA commands.

## Alternatives considered

- A database service would add durability infrastructure and credentials that are unnecessary for a shared repository workflow.
- A Python package dependency graph would increase onboarding cost for a small coordination CLI.
- A hidden daemon or model-specific scheduler would make the protocol less portable and harder to audit.

## Consequences

- A clone can be initialized with Python alone and inspected with ordinary text tools.
- JSON/Markdown merge cleanly in Git and remain readable to both humans and models.
- The CLI does not itself launch arbitrary external agents; a compatible runtime, scheduler or human must invoke workers.
- Large teams may later add a service adapter without changing the core file contract.

## Evidence / source anchors

- `tools/useagent.py:run_qa` and `tools/useagent.py:production_snapshot`
- `tests/test_useagent.py:UseAgentCliTests`
- `.github/workflows/ci.yml`
