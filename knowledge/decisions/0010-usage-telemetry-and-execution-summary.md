# ADR 0010: Provider-neutral usage telemetry and execution summaries

- **Status:** accepted
- **Date:** 2026-09-07
- **Work item:** UA-0059

## Context

Dogfood showed that supervisors need factual execution summaries, but agent
hosts expose different runtime metadata and often expose no machine-readable
token usage. Parsing provider prose would create false totals and privacy risk.
Lifecycle history already exists in the registry/report protocol, while
runtime diagnostics already have a bounded local spool.

## Decision

Add a small JSON event store at `work/telemetry/events.json`, ignored and
excluded from the release-source fingerprint. Task assignment/attempt/report
hooks and bounded supervisor cycles write metadata events. A stable event id
makes writes idempotent. Wall timestamps and durations are separate from
runner execution duration, and parallel worker runtime is never presented as
wall time.

Accept usage only from an explicit `relwit_usage: 1` JSON envelope at the
adapter/CLI boundary. Normalize optional token categories and provenance
(`authoritative`, `measured`, `estimated`, `unavailable`). Do not infer missing
fields, estimate by default, parse provider prose, store prompts or calculate
money. The supervisor report renders a bounded Usage section; the raw event
store is never dumped into owner-facing output.

## Alternatives rejected

- Scraping Codex/Claude/Antigravity/Gemini UI or prose: provider-coupled,
  brittle and not authoritative.
- Treating every missing token count as zero: false totals and misleading
  release decisions.
- Storing raw runner output in telemetry: duplicates the evidence boundary and
  increases secret leakage risk.
- Building billing, dashboards, leaderboards or remote analytics: outside this
  bounded phase and not needed for supervisor correctness.

## Consequences

ReleaseWitness can report measured timing and actual participation even when token
usage is unavailable. Partial usage is explicit. Existing runtime evidence and
release-source freshness remain independent. Future adapters can provide
authoritative usage without changing the core contract.
