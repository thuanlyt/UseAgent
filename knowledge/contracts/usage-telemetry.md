# ReleaseWitness Usage Telemetry Contract

Version: 1 (UA-0059)

ReleaseWitness telemetry is a small, provider-neutral execution record. It helps the
supervisor explain elapsed time, participation and efficiency signals after a
task or bounded cycle. It is not billing, quota management, a dashboard or a
quality score.

## Source of truth and privacy

The local event store is `work/telemetry/events.json`. It is runtime/control-
plane state, ignored by Git and excluded from the release-source fingerprint.
The store contains metadata only. Prompts, responses, credentials, account
identifiers and raw provider logs are never accepted as telemetry fields.
Raw diagnostics remain in the existing bounded local runtime spool.

## Normalized usage envelope

Only a complete JSON object with `relwit_usage: 1` is accepted at the adapter
boundary. The core never parses provider prose or scrapes a UI. The normalized
shape is:

```json
{
  "relwit_usage": 1,
  "authoritative": true,
  "provider": "provider-name",
  "runtime": "runtime-name",
  "model": "model-name",
  "input_tokens": 1000,
  "cached_input_tokens": 200,
  "output_tokens": 400,
  "reasoning_tokens": 50,
  "total_tokens": 1400
}
```

`input_tokens`, `output_tokens`, `cached_input_tokens`, `reasoning_tokens` and
`total_tokens` are optional non-negative integers. Missing categories remain
missing. A total that conflicts with both supplied input and output counts is
ambiguous and is recorded as unavailable. `authoritative: true` maps to
`authoritative`; an explicit `provenance` may be `measured` or `estimated`.
Estimation is never enabled implicitly. Missing, malformed, prose-only or
ambiguous usage is `unavailable`, never zero and never authoritative.

The CLI integration point is:

```powershell
relwit telemetry record --kind task --id RW-0001 `
  --event-id task:RW-0001:attempt:1 --agent worker-a --outcome completed `
  --usage-json '{"relwit_usage":1,"authoritative":true,"total_tokens":42}'
```

Configured runners may emit the same complete envelope as their entire
stdout/stderr result. There is no parser for Codex, Claude, Antigravity,
Gemini, or any provider-specific prose. Supervisor usage remains unavailable
unless its host exposes an equivalent machine-readable envelope and an
integration explicitly records it.

## Event and lifecycle semantics

Events are keyed by a stable `event_id`; an upsert replaces/extends that event
instead of appending a duplicate. Task attempt identity is
`task:<task-id>:attempt:<n>`. Assignment, claim/pull, report, retry and
takeover history are represented separately or on that attempt. Existing
history is not invented retroactively.

`started_at` and `completed_at` are UTC wall-clock timestamps. `duration_ms`
is measured wall duration when both timestamps are known. Runner subprocess
time is kept separately as `execution_duration_ms`; summing it is an aggregate
worker-runtime signal, not elapsed wall time. A cycle records one measured
wall interval, so two parallel workers do not turn a one-second cycle into a
two-second wall interval.

Participants are collected from assignment, task, runtime and review events,
not merely from the current `assigned_to` field. Optional provider, runtime,
model and role values are identifier-like metadata only.

## Aggregation and owner report

The supervisor report has a compact `Usage` section with measured wall time,
aggregate worker runtime, participants, task attempts/completions, failures,
retries and takeovers. Token status is explicitly `total`, `partial` or
`unavailable`. A partial known sum is not presented as a project total. Event
identity makes repeated report ingestion idempotent; different retry attempts
remain distinct. No monetary cost is calculated.

Use `relwit telemetry summary` for the same concise summary
without dumping the JSON event store.

## Release interaction

Telemetry writes are volatile and must not make source-bound QA stale. Changes
to the telemetry code, contract, tests or configuration remain release-source
changes and therefore require the normal QA and release gates.

### Hợp đồng tóm tắt bằng tiếng Việt

Telemetry chỉ ghi metadata thực tế: thời gian, agent/task tham gia và usage
token khi runtime cung cấp JSON có marker rõ ràng. Không đoán token, không đọc
prose của provider, không scrape UI và không lưu prompt/response/credential.
Thiếu hoặc mơ hồ là `unavailable`, không phải `0`. `duration_ms` là wall time;
`execution_duration_ms` là tổng thời gian runner, không được gọi là elapsed
time khi worker chạy song song. Event có `event_id` ổn định để chống cộng lặp;
retry/takeover vẫn giữ lineage. `work/telemetry/` là state local volatile,
không làm QA stale; thay đổi code/contract/test vẫn phải qua release gate.
