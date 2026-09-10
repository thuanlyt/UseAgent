# Knowledge model

## Index-first protocol

`knowledge/INDEX.md` is the router. A module card is a compressed map, not a replacement for source. Read the card, then verify only the source anchors that matter to the task.

## Module card fields

1. Responsibility — what the module owns and does not own.
2. Entry points — files, functions, routes, commands or events.
3. Public interfaces — contracts, schemas, inputs/outputs and compatibility constraints.
4. Dependency edges — upstream callers and downstream services/modules.
5. Invariants — behavior that must remain true.
6. Verification — focused commands and expected signal.
7. Known gaps — uncertainty, stale areas and follow-up tasks.

## Freshness

Use `freshness: verified|stale|bootstrap`, a date, an owner and at least one `path:symbol` source anchor. Mark stale when a relevant file, contract or build command changes. Prefer a small correction to a broad rewrite.

## Token budget

Return a compact snapshot: task scope, relevant cards, entry points, dependencies, acceptance and unknowns. Put raw logs in `work/evidence/`.
