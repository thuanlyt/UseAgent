# ADR-0008: Treat OSBlog as an evidence-frozen dogfood workload

- `Status`: accepted
- `Date`: 2026-09-06
- `Owner`: supervisor

## Context

OSBlog was the first substantial real workload used to exercise ReleaseWitness's
planning, multi-runtime dispatch, fallback, review, QA, production and resume
protocol. Its ledger contains useful positive and negative evidence: provider
unavailability, quota exhaustion, failed no-report attempts, supervisor
takeovers, a human interruption, real audits, live Vercel smoke and a blocked
Cap capture.

OSBlog production is Vercel-only for this case study. VPS, Netlify and local
Node are supported documentation targets, not environments that need live
verification. Continuing to implement every OSBlog portability backlog item
would obscure the product being evaluated: ReleaseWitness.

## Decision

1. Freeze OSBlog as a dogfood evidence source at its recorded release and
   recovery artifacts. Do not reopen OSBlog implementation unless a missing
   capture is required, a production defect invalidates the case study, or the
   user explicitly requests it.
2. Preserve failures, cancellations, blocked work, quota history, checkpoints
   and fallback attribution. A cancelled or blocked item is not silently
   converted into success because a later takeover worked.
3. Treat the OSBlog machine-readable registry and task/report evidence as the
   authority. Treat `work/SUPERVISOR_REPORT.md` as a generated convenience view
   that must advertise staleness if it no longer matches the registry.
4. Prioritize the following ReleaseWitness improvements: report freshness, worker
   runtime preflight, typed evidence provenance, CLI-managed takeover lineage,
   bounded media capture/privacy gates and compact cycle-overhead metrics.

## Evidence anchors

- OSBlog goal/roster/bootstrap: `work/reports/inbox/UA-0001-20260904T193501Z-9c2b22.md`, `UA-0002-20260904T193810Z-88fa19.md`
- Runtime limitation and replay recovery: `UA-0010.md`, `UA-0016-20260904T201341Z-be5f48.md`
- Audit → fix → review: `UA-0048-20260905T065104Z-9a279f.md`, `UA-0052-20260905T073012Z-f4a8c1.md`, `UA-0058-20260905T080830Z-07701a.md`
- Live/recovery release evidence: `UA-0040-20260905T084624Z-5b07cc.md`, `UA-0066-20260905T090716Z-e0114d.md`, `UA-0080-20260905T150650Z-f528ba.md`
- Capture boundary: `UA-0086-20260905T154011Z-61f28d.md`
- Quota failure and takeover: `UA-0091.md`, `UA-0093-20260905T204820Z-1826e7.md`
- Interruption and topology checkpoints: `20260905T204604Z-ua-0093-partial-implementation-recovery.md`, `20260905T205942Z-ua-0092-topology-and-trust-boundary-pass.md`

## Consequences

- ReleaseWitness documentation gains a real case study instead of only a replay
  fixture or product diagram.
- The case study remains honest about the difference between live Vercel
  evidence, local verification, simulation and blocked capture.
- The next implementation work returns to ReleaseWitness. OSBlog does not need a
  zero-backlog state for dogfooding to be complete.
