# Supervisor protocol

## Mailbox contract

Mỗi agent đăng ký có `INBOX.md`, `REPORT.md`, `COMPLETED.md` và `inbox/`. Supervisor là bên phát hành assignment; agent là bên ghi report. Người dùng đọc `work/SUPERVISOR_REPORT.md`.

## Assignment contract

Assignment phải có task id, objective, scope, acceptance, dependency, files/context cần đọc, command cần chạy, output bắt buộc và stop conditions. Assignment file là prompt đầy đủ để gửi cho worker.

## Optional runner contract

An agent may declare a `runner` object with an argv `command` array and a
positive `timeout_seconds`. The command must contain `{assignment_path}`. The
CLI substitutes that path plus `{task_id}` and `{agent_id}`, runs from the
selected project root with `shell=False`, writes a bounded sanitized summary
under `work/evidence/` and a separate bounded redacted diagnostic spool under
`work/.runtime-output/`. The spool is local-only and ignored by Git; the
summary carries its relative reference, stream sizes, preview budget,
truncation flags and typed local provenance. It invokes no runner when the
object is absent.

`worker run` is finite by default (`--max-tasks 1`, no idle wait). It pulls an
assigned task through the same claim checks as `worker pull`. The adapter must
submit `task report`; if it exits without a report, the CLI writes a failed
worker report so the task cannot remain silently active. The runner is an
explicit trusted integration boundary: the core protocol does not claim to
sandbox a vendor process or invent provider-specific flags.

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
`<!-- useagent-report: registry_sha256=<64-hex> -->` được tính từ registry snapshot
đã dùng để sinh report. `supervisor report --check` phải trả `fresh` (exit code 0)
mới được xem report là đồng bộ; `stale`, `unknown` hoặc `missing` không được coi là
trạng thái hiện tại. `context` hiển thị nhãn và cảnh báo freshness tương ứng.

## QA contract

`supervisor.qa_commands` is an array of shell command strings. Each command
runs from the repository root with the configured timeout. QA writes only
bounded sanitized stream summaries and metadata under `work/evidence/`; a
separate bounded redacted diagnostic spool under `work/.runtime-output/`
retains local debugging output. Each stream reports its captured size, preview
budget, redaction count and truncation flag. The cycle records `pass`, `fail`
or `not_configured`. This output boundary does not change the separate
trusted-local execution boundary of configured shell commands.

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
volatile control-plane paths are exempt from release-source cleanliness.

`supervisor.operational_readiness_files` is an array of non-empty repository-relative Markdown paths. The production snapshot marks the operational/rollback gate as `pass` only when every configured file exists and contains content; missing or unsafe paths remain `manual`.

## Supervisor cycle contract

Một cycle: ingest reports -> review trạng thái -> chạy QA được cấu hình -> dispatch task ready -> viết supervisor report -> checkpoint. Cycle không tự deploy và không tự chạy vô hạn. Worker runner nếu được bật cũng phải có timeout, max-tasks và idle wait hữu hạn.

## Stack decision contract

Khi goal là greenfield, supervisor phải xem constraint, deployment target, capability roster, testability và maintenance cost; chọn stack nhỏ nhất đáp ứng Definition of Done. Nếu repository đã có stack phù hợp, ưu tiên giữ stack đó. Ghi lựa chọn, assumption, rejected alternatives và source anchors vào `knowledge/project-brief.md`/`knowledge/decisions/`.
