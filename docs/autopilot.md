# Long-running autopilot

## Mô hình

Autopilot không phải một agent tự chạy mãi. Mỗi cycle có ngân sách và điểm kết thúc:

1. đọc `AGENTS.md`, `knowledge/INDEX.md`, `work/SUPERVISOR_REPORT.md`, registry và checkpoint gần nhất;
2. ingest report `.md` và chọn task `planned` không còn dependency;
3. dispatch tự động vào mailbox worker theo scope/capability;
4. đọc report completed, kiểm tra diff và chạy `qa_commands`;
5. tạo task debug khi QA/review fail, cập nhật knowledge và evidence;
6. tạo checkpoint bằng CLI;
7. dừng với `complete`, `blocked` hoặc `needs_input`.

## Prompt bền vững cho scheduled task

Trước khi tạo scheduled task, chạy prompt này thủ công và xem vài lần đầu:

```text
Use $useagent in F:\dev\UseAgent. Read AGENTS.md, knowledge/INDEX.md,
work/SUPERVISOR_REPORT.md, the latest checkpoint, and work/registry.json. Run
exactly one safe `python tools/useagent.py supervisor cycle --run-qa` cycle:
ingest worker report Markdown, inspect completed tasks, dispatch ready work to
eligible mailboxes, delegate independent exploration in parallel, ask workers to
report through the CLI, review evidence, create a debug task when QA fails,
refresh compact knowledge, and write a checkpoint. Stop with needs_input for
ambiguous acceptance, missing access, scope conflict, repeated failure, or any
deploy/destructive action. Do not edit outside a claimed scope. Return only a
concise summary, report/evidence paths, blockers and next action.
```

## Local project và worktree

Scheduled local work cần máy và app hoạt động. Với Git repository, chọn worktree cho run có thể sửa code khi local checkout đang có thay đổi; chọn local project chỉ khi chủ động cho phép task sửa working tree. Nếu dự án chưa dùng Git, giữ chính sách một writer mỗi scope và checkpoint thường xuyên.

## Safety gates

- Mỗi run hữu hạn task/cycle; không tự tăng concurrency.
- Không đánh dấu production-ready khi chưa có acceptance, regression, operational note và rollback plan.
- Không tự deploy hoặc thay đổi external system.
- Sau lỗi lặp lại, tạo blocker có giả thuyết đã thử thay vì tiếp tục lặp command.
