# OSBlog dogfooding case study

> Evidence-backed closeout of a real UseAgent run. Evidence freeze: 2026-09-06.
> The source workload was `thuanlyt/osblog`; its local checkout was
> `F:\dev\test-useagent` at commit `ea08ab3`. No secrets, credentials or raw
> browser profiles were copied into this repository.

## Why this case study exists

OSBlog was the real-world workload used to exercise UseAgent beyond a toy
fixture. The goal was an open-source, bilingual Markdown blog with a Vite +
React + TypeScript application, Neon/Postgres persistence, Better Auth admin
access, moderated email-only comments, SSR SEO, feeds, media and a Vercel
production deployment.

This document is a dogfood record, not a claim that every backlog item is
closed. OSBlog's live production target is Vercel:

- primary: `https://osblog.thuanlyt.id.vn`
- secondary alias: `https://osblog.vercel.app`

VPS, Netlify and local Node are documented deployment targets, not live OSBlog
environments. The remaining portability work is therefore a residual finding,
not a production blocker for the current Vercel workload.

## Evidence vocabulary

The case study keeps four kinds of evidence separate:

| Label | Meaning |
| --- | --- |
| **Verified** | A local command, test or review produced the recorded result. |
| **Live** | A read-only check observed the named Vercel deployment or public route. |
| **Simulation** | A replay or generated visual demonstrates the protocol but is not vendor execution. |
| **Blocked / residual** | The attempt or boundary is preserved, but the evidence is intentionally incomplete. |

The OSBlog registry and task Markdown are the source of truth. The supervisor
report is a convenience view and became stale after the late release-gate
work; that drift is itself a finding below.

## Workload and roster

The configured roster in
[`useagent.config.json`](https://github.com/thuanlyt/osblog/blob/main/useagent.config.json)
contained these identities:

| Identity | Intended role in the run | What the evidence proves |
| --- | --- | --- |
| `supervisor` | Plan, dispatch, review, QA and release decisions | Real supervisor reports, checkpoints and CLI transitions. |
| `antigravity` | Preferred full-stack worker | Registered in the roster; some requested runtime calls were unavailable, so no unavailable execution is fabricated. |
| `codex` | Frontend/backend/tests worker or fallback | Several real fallback and recovery tasks are explicitly labeled Codex. |
| `claude` | Backend/docs/tests worker | Real worker reports exist for implementation and documentation slices. |
| `supervisor-local` | Local takeover/recovery worker | Real takeover reports for slug history, Turnstile and the secondary-host fix. |
| `astra` / `astra-audit` | Independent implementation or review | Successful audits and review reports exist, plus preserved quota failures. |

The important result is not that every provider was always callable. It is
that the repository preserved the intended provider identity, the generated
assignment, the fallback reason and the final attribution when a runtime was
not available.

## Timeline

All timestamps below are UTC because the task ledger records `Z` timestamps.
Each row points to the OSBlog artifact that supports the statement.

| Time | Event | Result and evidence |
| --- | --- | --- |
| 2026-09-04 19:35 | Supervisor bootstrap | Goal, knowledge ledger, roster, operations notes and the first work items were created. [`UA-0001 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0001-20260904T193501Z-9c2b22.md) |
| 2026-09-04 19:38 | First dispatch cycle | The supervisor recorded concrete assignments for Antigravity, Codex and Claude, including runtime limits and a next ingestion action. [`UA-0002 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0002-20260904T193810Z-88fa19.md) |
| 2026-09-04 19:57–20:13 | Runtime unavailability and safe fallback | Antigravity/Claude were not callable in that environment. Failed fallback attempts were cancelled or preserved, then supervisor-local recovery created a real conformance replay with explicit simulation labels. [`UA-0010`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0010.md), [`UA-0014`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0014.md), [`UA-0016 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0016-20260904T201341Z-be5f48.md) |
| 2026-09-04 20:20–21:17 | Local implementation wave | The scaffold, persistence boundary, admin auth, content API, comments, SSR/SEO and public flow were delivered as separate scoped items with local evidence. [`UA-0020`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0020.md), [`UA-0024`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0024.md), [`UA-0026`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0026.md), [`UA-0028`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0028.md), [`UA-0030`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0030.md), [`UA-0033`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0033.md), [`UA-0034`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0034.md) |
| 2026-09-05 06:51 | Independent correctness audit | Astra reproduced four application defects: partial PATCH unpublishing, malformed cover URL SSR failure, dropped renewed auth cookies and a chunked-body timeout. [`UA-0048 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0048-20260905T065104Z-9a279f.md) |
| 2026-09-05 07:30–08:08 | Fix and independent re-review | Claude fixed the four findings with regressions; Astra re-ran runtime/lifecycle controls and preserved two UseAgent lifecycle P2 findings instead of declaring a clean slate. [`UA-0052 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0052-20260905T073012Z-f4a8c1.md), [`UA-0058 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0058-20260905T080830Z-07701a.md) |
| 2026-09-05 08:46–09:13 | Release, Vercel and recovery evidence | A release report recorded local tests/build/audit, two compiled-browser tests, conformance replay and both Vercel host smoke checks. A reversible alias rollback rehearsal passed; the first Neon backup/restore attempt was correctly blocked by missing provider/tool access rather than guessed. [`UA-0040 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0040-20260905T084624Z-5b07cc.md), [`UA-0066 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0066-20260905T090716Z-e0114d.md), [`UA-0068 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0068-20260905T091307Z-511e92.md) |
| 2026-09-05 14:45–15:23 | Slug-history takeover and live rollout | After a quota boundary, supervisor takeover completed the slug-history implementation, migration, redirect and current-route gates. The later rollout report records a disposable recovery rehearsal, production migration/replay, a READY Vercel deployment and both aliases' live smoke. A positive historical-308 fixture was not invented. [`UA-0077 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0077-20260905T144559Z-3f9ddf.md), [`UA-0080 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0080-20260905T150650Z-f528ba.md) |
| 2026-09-05 15:40–16:03 | Capture boundary and Turnstile gate | Cap itself was healthy, but the requested Brave/Cap target was unavailable; the fresh recording could not be proven to contain OSBlog and was not promoted. Turnstile was later independently release-gated locally with secret scans and 125 passing tests. [`UA-0086 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0086-20260905T154011Z-61f28d.md), [`UA-0089 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0089-20260905T160343Z-22903a.md) |
| 2026-09-05 15:45 | Independent production-gap audit | Astra identified the secondary-host interactive-form CSRF boundary, documented VPS forwarded-IP risk, stale/English-only documentation and missing browser performance evidence. No fresh Brave, Claude or Cap execution was falsely claimed. [`UA-0084 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0084-20260905T154550Z-9725e1.md) |
| 2026-09-05 20:39–20:48 | Quota failure, human interruption and takeover | Astra exhausted quota on UA-0091. The failure remained in history; a supervisor-local takeover completed the canonical-host fix with 15/15 focused runtime tests, typecheck, lint and security review. The partial and completion checkpoints show resume behavior. [`UA-0091`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0091.md), [`UA-0093 report`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0093-20260905T204820Z-1826e7.md), [`partial checkpoint`](https://github.com/thuanlyt/osblog/blob/main/work/checkpoints/20260905T204604Z-ua-0093-partial-implementation-recovery.md), [`completion checkpoint`](https://github.com/thuanlyt/osblog/blob/main/work/checkpoints/20260905T204821Z-ua-0093-canonical-host-fix-complete.md) |
| 2026-09-05 20:59 | Trust-boundary re-anchor | UA-0092 was deliberately not claimed. Evidence showed Vercel and the documented VPS target are different topologies; the unknown VPS path was recorded as non-blocking portability hardening rather than a reason to hunt for a live server. [`UA-0092`](https://github.com/thuanlyt/osblog/blob/main/work/items/UA-0092.md), [`topology checkpoint`](https://github.com/thuanlyt/osblog/blob/main/work/checkpoints/20260905T205942Z-ua-0092-topology-and-trust-boundary-pass.md) |

## What the run proved

### Planning and dispatch

The run started from a light goal and a roster. The supervisor created a
dependency-aware sequence, generated worker mailboxes and preserved copyable
prompts. The human supplied runtime access where it existed; the worker did
not need to invent a second task description.

### Provider-neutral execution

Codex, Claude and Antigravity-style identities could share the same repository
protocol because assignment, scope, report and evidence were Markdown/JSON
contracts. When a provider runtime was unavailable, the system retained the
original identity and labeled the fallback. That distinction made the final
case study credible.

### Audit-to-fix feedback

The strongest loop was:

```text
independent audit
    → reproducible finding
    → scoped implementation
    → regression test
    → independent re-review
```

The UA-0048 → UA-0052 → UA-0058 sequence demonstrates that “completed” did
not automatically mean “verified”. The same pattern reappeared in the
UA-0091 → UA-0093 quota recovery.

### Production and evidence boundaries

The workload reached a Vercel release candidate with both public aliases,
Neon-backed health, SSR routes, feeds, sitemap, robots and committed Cap
media smoke evidence. It also kept explicit boundaries: no live VPS claim,
no positive historical alias fixture created only for testing, no fresh Cap
capture when the frame could not be verified, and no provider execution claim
for unavailable runtimes.

## Findings from dogfooding

| ID | Finding | Impact | Evidence |
| --- | --- | --- | --- |
| F-01 | Durable task/report/checkpoint files preserve failure, recovery and attribution better than chat alone. | **Strength** — a new supervisor can resume without trusting memory. | UA-0010, UA-0016, UA-0091, UA-0093 checkpoints. |
| F-02 | Independent review plus CLI evidence catches real defects that a successful worker report would miss. | **Strength** — release confidence improves through audit → fix → re-review. | UA-0048, UA-0052, UA-0058. |
| F-03 | Fallback attribution is useful, but runtime availability was discovered late and caused waits, cancelled items and manual recovery. | **Friction** — human supervision and task churn increase. | UA-0003, UA-0006, UA-0013, UA-0015, UA-0019, UA-0010. |
| F-04 | `work/SUPERVISOR_REPORT.md` became stale after later registry changes: it still described old test counts and Turnstile status while UA-0089/UA-0093 had newer evidence. | **P1 product gap** — a user reading only the convenience report can make a wrong decision. | OSBlog `work/SUPERVISOR_REPORT.md` compared with registry and UA-0089/UA-0093. |
| F-05 | A partial edit plus a user Stop was recoverable through a checkpoint and takeover, but only after a human gave precise resume instructions. | **P1 workflow gap** — interruption safety is good when disciplined, not yet automatic. | UA-0093 partial/completion checkpoints. |
| F-06 | Cap health did not imply a capturable, verifiable browser target. | **P2 evidence gap** — recording output can exist without proving its content. | UA-0086 report and `docs/media.md`. |
| F-07 | The task ledger grew to 93 items, including 29 cancelled and 2 blocked states, across fallback, takeover and release work. | **P2 overhead** — history is valuable but current-state scanning becomes expensive. | OSBlog `work/registry.json` at evidence freeze. |
| F-08 | The first UA-0092 topology pass over-scoped an undocumented VPS concern until the correction re-anchored OSBlog to Vercel-only production. | **Process finding** — environment assumptions can pull the supervisor away from the real goal. | UA-0092 topology checkpoint and re-anchor decision. |

## What changed in UseAgent after dogfooding

The case study is now a record of the improvements it triggered, not a stale
to-do list. These changes are shipped in the current UseAgent release; they do
not reopen OSBlog implementation work.

| Status | Shipped change or residual | Why it follows from OSBlog |
| --- | --- | --- |
| Shipped | Report freshness, typed evidence provenance and CLI-managed takeover lineage (`UA-0048`–`UA-0050`). | Keeps the registry authoritative, labels evidence honestly and preserves quota/interruption history. |
| Shipped | Sanitized bounded evidence with an ignored local runtime spool (`UA-0051`). | Prevents raw runner/QA output from becoming repository evidence by default. |
| Shipped | Source-bound QA and Git release durability (`UA-0052`–`UA-0053`). | Prevents a passing or completed state from being mistaken for verification of a different source snapshot. |
| Shipped | Safe QA argv execution and bounded worker runtime readiness/failure classification (`UA-0054`–`UA-0055`). | Reduces shell ambiguity, blind dispatch and unsupported quota/auth guesses. |
| Residual | Filesystem sandboxing, authenticated remote identity, stale-lock recovery, CI action SHA pinning, capture verification and cycle metrics remain backlog. | These are useful higher-assurance or operational improvements, but none is required to claim the trusted-local UseAgent dogfood closeout. |

## OSBlog handover after closeout

OSBlog is handed over as a real dogfood result, not as an unfinished feature
backlog:

- **Verified/live evidence:** Vercel primary and alias smoke, Neon-backed
  release evidence, SSR/SEO/feed/media routes, local tests/build/typecheck/lint,
  audit, conformance replay, worker reports, reviews, quota failure and
  takeover history.
- **Residual:** UA-0092 is planned, non-blocking documented-VPS portability
  hardening. No live VPS is required for the case study.
- **Residual:** UA-0080 does not claim a positive historical `308` fixture
  because no production content was created solely for testing.
- **Residual:** UA-0086 does not claim a fresh Cap capture; existing committed
  media remains valid evidence, while the new unverified capture stays blocked.
- **Important boundary:** later local hardening (including UA-0093) must not be
  described as deployed unless a later Vercel deployment record proves it.

The next useful work belongs in the UseAgent repository: choose from the
remaining higher-assurance backlog only when its threat model and evidence
justify it. Do not reopen OSBlog implementation merely to drive its backlog to
zero.

## Tóm tắt tiếng Việt

### Mục đích

OSBlog là workload thật để kiểm chứng UseAgent. Mục tiêu là xây dựng blog
Markdown mã nguồn mở, song ngữ, có Vite + React + TypeScript, Neon/Postgres,
Better Auth, comment có kiểm duyệt, SSR SEO, feed, media và deploy Vercel.

Production hiện tại chỉ có hai hostname Vercel:

- `https://osblog.thuanlyt.id.vn`
- `https://osblog.vercel.app`

VPS, Netlify và Node local chỉ là target được tài liệu hỗ trợ, không phải môi
trường live của OSBlog.

### Timeline rút gọn

1. Supervisor bootstrap goal, roster, knowledge ledger và DAG bằng UA-0001/UA-0002.
2. Antigravity/Claude không callable trong một số thời điểm; UseAgent giữ lại
   assignment, hủy đúng cách và ghi rõ Codex/supervisor-local fallback.
3. Các worker xây scaffold, persistence, auth, CRUD, comment, SSR/SEO và UI
   theo scope riêng.
4. Astra audit tìm bốn lỗi thật; Claude sửa; Astra re-review bằng test độc lập.
5. Release gate, Vercel smoke, rollback rehearsal, migration/replay và slug
   history được ghi bằng evidence riêng.
6. Cap mới bị block vì không có browser target xác minh được; media cũ hợp lệ
   vẫn được giữ nguyên.
7. Astra hết quota ở UA-0091; UA-0093 takeover sau checkpoint và hoàn tất
   canonical-host fix mà không nới CSRF.
8. UA-0092 được re-anchor: chỉ là VPS portability hardening, không phải blocker
   của Vercel production.

### Findings chính

- Điểm mạnh: file ledger, report, review và checkpoint giúp giữ attribution,
  failure history và recovery có thể kiểm tra.
- Ma sát: runtime provider unavailable gây wait/fallback/cancel; con người phải
  cung cấp resume instruction chính xác.
- Đã ship: supervisor report có freshness marker, evidence có provenance kiểu rõ
  và interruption/takeover lineage được quản lý trong registry.
- Đã ship: evidence runtime được giới hạn, sanitize và giữ raw diagnostic ở
  local spool bị ignore; QA/release được bind vào source state hiện tại.
- Khoảng trống P2: Cap cần target discovery, privacy gate và content verification.
- Overhead: ledger lớn giúp audit nhưng làm việc đọc current state tốn hơn.

### Hướng cải tiến UseAgent

Report freshness, evidence provenance, takeover lineage, evidence hygiene,
source-bound QA, Git durability, safe QA và runtime readiness đã được đưa vào
UseAgent qua UA-0048–UA-0055. Các khoảng trống còn lại gồm sandbox/diff
enforcement, identity xác thực, stale-lock recovery, CI action SHA, capture
verification và cycle metrics. Đây là backlog của UseAgent, không phải lý do để
mở rộng lại OSBlog.

## Source anchors

- Dogfood repository: [`thuanlyt/osblog`](https://github.com/thuanlyt/osblog)
- OSBlog supervisor report: [`work/SUPERVISOR_REPORT.md`](https://github.com/thuanlyt/osblog/blob/main/work/SUPERVISOR_REPORT.md)
- OSBlog registry: [`work/registry.json`](https://github.com/thuanlyt/osblog/blob/main/work/registry.json)
- Existing media provenance: [`docs/media.md`](https://github.com/thuanlyt/osblog/blob/main/docs/media.md)
- UseAgent visual/demo contract: [`knowledge/decisions/0007-visual-documentation-system.md`](../knowledge/decisions/0007-visual-documentation-system.md)
