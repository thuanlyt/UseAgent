# Decision 0009: Supervisor judgment and owner communication

- **Status:** accepted
- **Date:** 2026-09-07
- **Owner:** supervisor
- **Source:** `knowledge/contracts/supervisor-judgment.md`

## Context

The existing UseAgent supervisor contract covered planning, dispatch, evidence,
review, QA and release gates, but treated owner proposals, preferences,
constraints, tradeoffs and stop decisions implicitly. That encouraged checklist
completion and made it harder to preserve decision quality across cycles.

## Decision

Keep judgment as a model-facing contract rather than adding a second runtime
state machine. Establish one canonical contract that requires the Supervisor to
classify intent, challenge materially weak proposals, recommend a default with
relevant tradeoffs, ask only decision-critical questions, respect explicit
owner decisions, verify worker/audit claims and stop when marginal value no
longer justifies cost or risk. Other skills reference this contract through
progressive disclosure.

The CLI remains responsible for deterministic state, scope, evidence and
release authorization. It does not pretend to evaluate model reasoning.

## Rejected alternatives

- **Duplicate the doctrine in every skill:** increases prompt size and creates
  contradiction risk.
- **Encode judgment as new CLI statuses:** confuses human decision quality with
  deterministic task lifecycle and would enlarge the control plane without
  proving better decisions.
- **Always ask the owner:** adds latency and token cost for decisions that
  repository evidence can settle.
- **Always choose autonomously:** violates owner authority for preference,
  direction, authorization and irreversible actions.

## Consequences

- Supervisor prompts and handovers have an explicit decision vocabulary and
  concise owner communication format.
- Tests can validate contract structure and conformance scenario coverage, but
  not subjective model intelligence.
- Higher-assurance sandboxing, authenticated identity, provider management,
  stale-lock recovery and OSBlog work remain outside this decision.
