# Supervisor protocol

## Mailbox contract

Mỗi agent đăng ký có `INBOX.md`, `REPORT.md`, `COMPLETED.md` và `inbox/`. Supervisor là bên phát hành assignment; agent là bên ghi report. Người dùng đọc `work/SUPERVISOR_REPORT.md`.

## Assignment contract

Assignment phải có task id, objective, scope, acceptance, dependency, files/context cần đọc, command cần chạy, output bắt buộc và stop conditions. Assignment file là prompt đầy đủ để gửi cho worker.

## Report contract

Report phải có task id, agent, result (`completed|blocked|failed`), summary, files, checks/evidence, blockers và next action. `completed` chỉ là worker report; supervisor/reviewer mới quyết định `done`. `task report` tự append vào `work/agents/<agent>/REPORT.md`, `work/reports/REPORTS.md` và `work/completed/COMPLETED.md` khi phù hợp.

## QA contract

`supervisor.qa_commands` is an array of shell command strings. Each command runs from the repository root with the configured timeout; stdout/stderr are saved under `work/evidence/` and the cycle records `pass`, `fail` or `not_configured`.

`supervisor.operational_readiness_files` is an array of non-empty repository-relative Markdown paths. The production snapshot marks the operational/rollback gate as `pass` only when every configured file exists and contains content; missing or unsafe paths remain `manual`.

## Supervisor cycle contract

Một cycle: ingest reports -> review trạng thái -> chạy QA được cấu hình -> dispatch task ready -> viết supervisor report -> checkpoint. Cycle không tự deploy và không tự chạy vô hạn.

## Stack decision contract

Khi goal là greenfield, supervisor phải xem constraint, deployment target, capability roster, testability và maintenance cost; chọn stack nhỏ nhất đáp ứng Definition of Done. Nếu repository đã có stack phù hợp, ưu tiên giữ stack đó. Ghi lựa chọn, assumption, rejected alternatives và source anchors vào `knowledge/project-brief.md`/`knowledge/decisions/`.
