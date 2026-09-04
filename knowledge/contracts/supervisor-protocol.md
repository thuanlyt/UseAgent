# Supervisor protocol

## Mailbox contract

Mỗi agent đăng ký có `INBOX.md`, `REPORT.md`, `COMPLETED.md` và `inbox/`. Supervisor là bên phát hành assignment; agent là bên ghi report. Người dùng đọc `work/SUPERVISOR_REPORT.md`.

## Assignment contract

Assignment phải có task id, objective, scope, acceptance, dependency, files/context cần đọc, command cần chạy, output bắt buộc và stop conditions. Assignment file là prompt đầy đủ để gửi cho worker.

## Optional runner contract

An agent may declare a `runner` object with an argv `command` array and a
positive `timeout_seconds`. The command must contain `{assignment_path}`. The
CLI substitutes that path plus `{task_id}` and `{agent_id}`, runs from the
selected project root with `shell=False`, captures bounded stdout/stderr under
`work/evidence/` and invokes no runner when the object is absent.

`worker run` is finite by default (`--max-tasks 1`, no idle wait). It pulls an
assigned task through the same claim checks as `worker pull`. The adapter must
submit `task report`; if it exits without a report, the CLI writes a failed
worker report so the task cannot remain silently active. The runner is an
explicit trusted integration boundary: the core protocol does not claim to
sandbox a vendor process or invent provider-specific flags.

## Report contract

Report phải có task id, agent, result (`completed|blocked|failed`), summary, files, checks/evidence, blockers và next action. Worker chỉ report sau khi task đã được claim/pull sang `in_progress`; `completed` chỉ là worker report; supervisor/reviewer mới quyết định `done`. `task report` tự append vào `work/agents/<agent>/REPORT.md`, `work/reports/REPORTS.md` và `work/completed/COMPLETED.md` khi phù hợp. Không dùng `task update --status reported`; CLI từ chối transition này để mọi trạng thái `reported` đều có report path xác thực.

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

## QA contract

`supervisor.qa_commands` is an array of shell command strings. Each command runs from the repository root with the configured timeout; stdout/stderr are saved under `work/evidence/` and the cycle records `pass`, `fail` or `not_configured`.

`supervisor.operational_readiness_files` is an array of non-empty repository-relative Markdown paths. The production snapshot marks the operational/rollback gate as `pass` only when every configured file exists and contains content; missing or unsafe paths remain `manual`.

## Supervisor cycle contract

Một cycle: ingest reports -> review trạng thái -> chạy QA được cấu hình -> dispatch task ready -> viết supervisor report -> checkpoint. Cycle không tự deploy và không tự chạy vô hạn. Worker runner nếu được bật cũng phải có timeout, max-tasks và idle wait hữu hạn.

## Stack decision contract

Khi goal là greenfield, supervisor phải xem constraint, deployment target, capability roster, testability và maintenance cost; chọn stack nhỏ nhất đáp ứng Definition of Done. Nếu repository đã có stack phù hợp, ưu tiên giữ stack đó. Ghi lựa chọn, assumption, rejected alternatives và source anchors vào `knowledge/project-brief.md`/`knowledge/decisions/`.
