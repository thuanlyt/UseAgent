# Supervisor protocol

## Mailbox contract

Mỗi agent đăng ký có `INBOX.md`, `REPORT.md`, `COMPLETED.md` và `inbox/`. Supervisor là bên phát hành assignment; agent là bên ghi report. Người dùng đọc `work/SUPERVISOR_REPORT.md`.

## Supervisor judgment and owner communication

The canonical [Supervisor Judgment and Owner Communication contract](supervisor-judgment.md)
defines how the model separates outcomes, constraints, preferences, proposed
solutions and explicit owner decisions; weighs tradeoffs; recommends or
escalates; handles worker/audit claims; communicates concisely; and stops when
marginal value is low. This is model-facing guidance layered above the
deterministic CLI state/evidence/authorization rules below.

## Assignment contract

Assignment phải có task id, objective, scope, acceptance, dependency, files/context cần đọc, command cần chạy, output bắt buộc và stop conditions. Assignment file là prompt đầy đủ để gửi cho worker.

## Optional runner and runtime-readiness contract

An agent may declare a `runner` object with an argv `command` array and a
positive `timeout_seconds`. The command must contain `{assignment_path}`. The
CLI substitutes that path plus `{task_id}` and `{agent_id}`, runs from the
selected project root with `shell=False`, writes a bounded sanitized summary
under `work/evidence/` and a separate bounded redacted diagnostic spool under
`work/.runtime-output/`. The spool is local-only and ignored by Git; the
summary carries its relative reference, stream sizes, preview budget,
truncation flags and typed local provenance. It invokes no runner when the
object is absent.

An optional preflight is an argv-only adapter probe:

```json
{
  "preflight": {
    "command": ["python", "adapter.py", "--preflight", "{agent_id}"],
    "timeout_seconds": 30
  }
}
```

ReleaseWitness performs static validation and executable checks before dispatch. A
configured but clearly unavailable or malformed runner is not assigned work.
When a task is already assigned, `worker run` executes the bounded preflight
before changing `assigned` to `in_progress`. The probe must print one complete
JSON object such as `{"relwit_preflight":1,"state":"ready"}`. `state` is
one of `ready`, `unavailable`, `misconfigured`, `no_target` or `unknown`.
`ready` means only that the declared local adapter prerequisites passed; it
does not predict provider quota or model availability. Invalid, ambiguous or
timed-out probes are recorded as bounded local diagnostics and do not silently
claim runtime ownership. A missing preflight means `unknown` with the legacy
runner compatibility path, so existing adapters continue to work.

Adapters may classify a started-runner failure with one complete JSON object:

```json
{
  "relwit_runtime_result": 1,
  "failure_class": "quota_limited",
  "authoritative": true,
  "disposition": "needs_input",
  "reason": "provider contract quota"
}
```

Supported classes are `unavailable`, `no_target`, `misconfigured`,
`auth_error`, `quota_limited`, `timeout`, `runtime_error` and `unknown`.
`quota_limited` and `auth_error` are accepted only with an explicit
`authoritative: true` machine-readable adapter result. Human-readable stderr
or provider-shaped text is never enough and is downgraded to a generic/unknown
failure. Recommended bounded dispositions are `retry`, `reassign`,
`takeover` or `needs_input`; the CLI records the recommendation but never
creates an infinite retry loop or a successor automatically.

The ownership sequence is `planned -> assigned -> readiness -> in_progress ->
reported`. A pre-start readiness failure leaves the task `assigned`, appends
sanitized runtime evidence and a local-spool reference, and gives the
supervisor a disposition. A process start failure after pull is classified and
the existing no-report safeguard writes a failed worker report, so there is no
unowned `in_progress` task or report-wait dead end. The adapter remains the
provider-specific boundary: ReleaseWitness does not invent Codex/Claude/Antigravity
flags, call vendor APIs or claim to sandbox a vendor process.

`worker run` is finite by default (`--max-tasks 1`, no idle wait). It pulls an
assigned task through the same claim checks as `worker pull`. The adapter must
submit `task report`; if it exits without a report, the CLI writes a failed
worker report so the task cannot remain silently active. Readiness and runner
diagnostics use the UA-0051 bounded/sanitized output contract and are volatile
control-plane writes, so they do not change the UA-0052 release-source
fingerprint. The configured runner/preflight shape remains part of source/config
identity and is validated before use.

## Report contract

Report phải có task id, agent, result (`completed|blocked|failed`), summary, files, checks/evidence, blockers và next action. Worker chỉ report sau khi task đã được claim/pull sang `in_progress`; `completed` chỉ là worker report; supervisor/reviewer mới quyết định `done`. `task report` tự append vào `work/agents/<agent>/REPORT.md`, `work/reports/REPORTS.md` và `work/completed/COMPLETED.md` khi phù hợp. Không dùng `task update --status reported`; CLI từ chối transition này để mọi trạng thái `reported` đều có report path xác thực.

`task report` accepts an optional controlled `--provenance` and single-line
`--source`; the generated report frontmatter and registry evidence carry both
fields plus `recorded_at`. Reports authored before this contract may omit the
fields and are ingested as `legacy`, so they remain readable without being
upgraded to a stronger claim.

Supervisor chỉ ingest report có result hợp lệ, agent đã đăng ký, agent trùng
`assigned_to` của task đang active và các file khai báo nằm trong task scope.
File không an toàn hoặc ngoài scope bị bỏ qua và được ghi warning evidence để
reviewer nhìn thấy; report không hợp lệ, không đọc được hoặc nằm ngoài project
root bị bỏ qua an toàn và không được dùng để chuyển trạng thái. Roster/task
collection malformed không được làm ingest, pull hoặc dispatch traceback.

Task phải đi qua `needs_review` trước khi trở thành `done`. Worker không được
tự biến report `completed` thành release decision; review evidence là điều kiện
bắt buộc của trạng thái `done`; review evidence phải có giá trị không rỗng.
Task phải ở trạng thái `reported` trước khi reviewer chuyển sang `needs_review`;
không được bỏ qua worker report bằng transition trực tiếp từ `in_progress`.
`done` và `cancelled` là trạng thái kết thúc; không được reopen bằng
`task update`.
Khi một attempt `blocked` hoặc `cancelled` cần recovery, supervisor tạo task
mới bằng `task new --supersedes <id> --takeover-reason "..."`. CLI giữ nguyên
failure history và ghi liên kết hai chiều (`supersedes`/`superseded_by`) cùng
reason trong registry và Markdown items. Predecessor active hoặc `done` không
thể bị takeover; predecessor đã có successor không được claim hoặc đưa lại về
`planned`. Thiếu predecessor, reason, reciprocal link hoặc single-line shape
là lỗi validation, không được làm đổi state.
Roster chỉ chấp nhận các role `supervisor`, `explorer`, `planner`, `worker`,
`reviewer` và `release_gate`; reviewer/release gate không được claim hoặc
report task implementation.
`assigned -> in_progress` chỉ qua `task claim`/`worker pull`; transition
`planned`, `blocked` hoặc `cancelled` bằng `task update` là thao tác hành chính
và cần identity review-capable. Worker dùng `task report --result blocked`.
`task claim` và `worker pull` đều phải kiểm tra agent đang `available`, chưa vượt
`max_active`, đúng scope/capability của task; từ chối xảy ra trước khi đổi state.
Chỉ agent đã đăng ký có role `supervisor`,
`reviewer` hoặc `release_gate` mới được ghi evidence `kind=review` và chuyển
task `reported` qua `needs_review` đến `done`. Reviewer có thể khác với worker
được giao task; worker chỉ được report kết quả và thêm evidence triển khai/test.

`work/registry.json` và task evidence luôn có authority cao hơn
`work/SUPERVISOR_REPORT.md`. Report là convenience view có marker
`<!-- relwit-report: registry_sha256=<64-hex> -->` được tính từ registry snapshot
đã dùng để sinh report. `supervisor report --check` phải trả `fresh` (exit code 0)
mới được xem report là đồng bộ; `stale`, `unknown` hoặc `missing` không được coi là
trạng thái hiện tại. `context` hiển thị nhãn và cảnh báo freshness tương ứng.

## QA contract

`supervisor.qa_commands` is an array of explicit command objects. The default
shape is `{ "mode": "argv", "argv": ["program", "arg1", ...] }`; it runs from
the repository root with `shell=False`, so arguments are passed literally and
shell metacharacters are not interpreted. Shell syntax is available only through
the explicit trusted-local shape `{ "mode": "shell", "command": "..." }`.
Shell mode is repository/operator code execution, not a sandbox or an
authentication boundary. Legacy command strings are rejected by validation and
are never heuristically split or silently promoted to shell execution.

Each command runs with the configured timeout. QA writes only bounded sanitized
stream summaries and metadata under `work/evidence/`; a separate bounded
redacted diagnostic spool under `work/.runtime-output/` retains local debugging
output. Each stream reports its captured size, preview budget, redaction count
and truncation flag, and each result records `execution_mode`. The cycle records
`pass`, `fail` or `not_configured`. Both execution modes retain the UA-0051
output boundary.

The existing UA-0052 release-source fingerprint includes the complete QA
configuration, so command argv, execution mode, timeout and related QA/release
configuration changes invalidate an older QA result without introducing a
second fingerprint.

Successful QA also records a release-source fingerprint. The fingerprint
includes Git `HEAD` when available, content hashes for tracked and non-ignored
untracked files, the current dirty-state equivalent and the QA/release
configuration. `release_source.volatile_paths` is an explicit, validated
configuration of control-plane paths excluded from that fingerprint; generated
registry, report, checkpoint, evidence and runtime updates must not
self-invalidate QA. A missing or mismatched fingerprint is `QA_STALE`; the
production snapshot fails closed and never reruns QA implicitly.

Task completion, QA validity and local release durability are separate
decisions. The production snapshot adds a `release_source_durability` gate. In
a Git-backed repository it passes only when a concrete `HEAD` exists, all
release-relevant tracked state is clean, no non-ignored untracked release
source exists, and the current QA source fingerprint is valid. A QA pass on a
dirty tree may remain valid for development, but strong release readiness must
reject it. A later commit changes source identity, so QA must be rerun rather
than silently reused.

The release snapshot records branch, locally configured upstream and
ahead/behind relation without contacting or mutating a remote. Local
durability does not require `HEAD == origin/main`; ahead, behind and diverged
metadata are informational. No upstream is represented as `none`, and missing
tracking metadata is explicit. A non-Git workspace is `filesystem`/`manual`
degraded mode and never claims strong Git durability. Only the configured
volatile control-plane paths, including `work/SUPERVISOR_REPORT.md`, are exempt
from release-source cleanliness.

`supervisor.operational_readiness_files` is an array of non-empty repository-relative Markdown paths. The production snapshot marks the operational/rollback gate as `pass` only when every configured file exists and contains content; missing or unsafe paths remain `manual`.

## Supervisor cycle contract

Một cycle: ingest reports -> review trạng thái -> chạy QA được cấu hình -> dispatch task ready -> viết supervisor report -> checkpoint. Cycle không tự deploy và không tự chạy vô hạn. Worker runner nếu được bật cũng phải có timeout, max-tasks và idle wait hữu hạn.

## Usage telemetry contract

ReleaseWitness ghi execution metadata vào `work/telemetry/` (volatile, Git-ignored):
task/cycle timing, actual participants, attempts, failures, retries và
takeover lineage. `duration_ms` là measured wall time; runner
`execution_duration_ms` là aggregate worker-runtime signal và không thay thế
wall time khi worker chạy song song. Event identity ổn định giúp repeated
writes không double-count.

Token usage chỉ được nhận từ complete JSON có `relwit_usage: 1` tại adapter
boundary. `authoritative`, `measured`, `estimated` và `unavailable` phải được
phân biệt; default không estimate. Provider prose, UI scrape, prompt,
response, credential và raw provider log không được đưa vào telemetry. Report
chỉ hiển thị Usage summary bounded; khi thiếu dữ liệu phải ghi
`partial`/`unavailable`, không biến known sum thành project total. Xem
`knowledge/contracts/usage-telemetry.md`.

## Stack decision contract

Khi goal là greenfield, supervisor phải xem constraint, deployment target, capability roster, testability và maintenance cost; chọn stack nhỏ nhất đáp ứng Definition of Done. Nếu repository đã có stack phù hợp, ưu tiên giữ stack đó. Ghi lựa chọn, assumption, rejected alternatives và source anchors vào `knowledge/project-brief.md`/`knowledge/decisions/`.
