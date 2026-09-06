# Changelog

All notable changes to UseAgent are documented here.

## [0.1.0] - 2026-09-07

Initial public release of UseAgent, a file-first multi-agent control plane for coordinating coding agents and humans in one repository.

### Added

- Scoped, dependency-aware work items with durable registry, mailboxes, reports and bounded supervisor cycles.
- Review and evidence gates with typed provenance, report freshness and takeover/failure lineage.
- Bounded, sanitized runner and QA summaries with detailed diagnostics kept in a local runtime spool.
- Source-bound QA, Git release durability checks and argv-first QA execution by default.
- Optional trusted-local shell execution, worker readiness checks and provider-neutral failure classification.
- Supervisor Judgment and Owner Communication contract for recommendations, tradeoffs, escalation and owner overrides.
- Provider-neutral usage telemetry for measured timing, participants, attempts, retries and takeovers; authoritative token usage is recorded only when a runtime supplies it.

### Reliability / Security

- Release and QA decisions are explicit, bounded and tied to the verified source state.
- The supported threat model is trusted-local / trusted-repository. UseAgent is not an OS sandbox, authenticated agent identity system, provider quota manager, mutually-untrusted isolation boundary, autonomous infinite swarm or deployment authority.
- Raw runtime output and telemetry remain local by default; durable evidence is bounded and sanitized.

### Documentation

- Canonical English and Vietnamese README files with matching capability, trust-model and release guidance.
- Practical Codex, Claude Code and Antigravity-style onboarding and conformance documentation.
- Operations, autopilot, release-integrity and OSBlog dogfood case-study documentation.

[0.1.0]: https://github.com/thuanlyt/UseAgent/releases/tag/v0.1.0
