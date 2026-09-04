# UseAgent architecture / Kiến trúc UseAgent

## English

UseAgent is a repository-local coordination layer. It does not replace the model that plans work or the runtime that executes a worker. It makes their shared state explicit, durable and reviewable.

### Layers

1. **Supervisor skill** — interprets the user's goal, records assumptions, derives milestones and decides the next bounded action.
2. **Specialist skills** — context, orchestration, worker implementation, review and autopilot provide narrow operating instructions.
3. **Control-plane CLI** — `tools/useagent.py` validates transitions, claims, scope ownership, dispatches assignments, ingests reports and runs configured QA.
4. **Knowledge ledger** — `knowledge/` stores compact, source-anchored context so agents do not reread unrelated files.
5. **Work ledger** — `work/` stores registry state, work items, mailboxes, reports, evidence and checkpoints.
6. **Repository rules** — `AGENTS.md` defines the safety boundary: explicit scope, one writer, evidence-backed handover and no unapproved side effects.

### State ownership

`work/registry.json` is the machine-readable source of truth for task state. Each task also has `work/items/<task-id>.md` for readable acceptance criteria and handover. Markdown reports are append-oriented communication artifacts; they do not silently override the registry.

The CLI uses atomic replacement for files and a short-lived exclusive lock for state transitions. The lock is released before worker code, tests or external processes run. Paths from configuration are resolved and rejected if they leave the repository root.

### Scheduling model

The supervisor selects tasks that are `planned` and whose dependencies are complete. A worker is eligible when it is available, below `max_active`, matches the task's preferred agent/capability constraints, and has no overlapping active writer scope. A dispatch writes both a mailbox assignment and an outbox prompt, then marks the task `assigned`.

The worker claims through `worker pull` or `task claim`, which changes `assigned` to `in_progress`. It may report through `task report` only after that activation; the command writes the report inbox, per-agent report/completed files, global completed log, report index and task handover metadata.

### Production gates

The default gates are intentionally conservative:

- every acceptance criterion has repeatable evidence;
- focused and integration QA pass;
- no open P0/P1 review finding;
- operational and rollback notes exist.

Deployment remains outside the CLI. A supervisor may recommend a release only after the gates are evidenced and the user explicitly authorizes external side effects.

## Tiếng Việt

UseAgent là lớp điều phối nằm trong repository. Nó không thay thế model lập kế hoạch hoặc runtime thực thi worker; nó làm cho state chung trở nên rõ ràng, bền vững và có thể review.

### Các lớp kiến trúc

1. **Supervisor skill** hiểu goal, ghi assumption, lập milestone và chọn hành động hữu hạn tiếp theo.
2. **Specialist skills** gồm context, orchestrator, worker, review và autopilot.
3. **CLI control plane** kiểm tra transition, claim, ownership scope, dispatch, ingest report và QA.
4. **Knowledge ledger** trong `knowledge/` lưu ngữ cảnh cô đọng có source anchor.
5. **Work ledger** trong `work/` lưu registry, work item, mailbox, report, evidence và checkpoint.
6. **Repository rules** trong `AGENTS.md` áp dụng scope rõ ràng, một writer, handover có bằng chứng và cấm side effect chưa được phép.

### Giao thức file

`work/registry.json` là nguồn sự thật dạng máy cho trạng thái task. Mỗi task có thêm `work/items/<task-id>.md` để người và model đọc acceptance criteria. Report Markdown là artifact giao tiếp; không được dùng để âm thầm ghi đè registry.

CLI ghi file theo cách atomic, dùng exclusive lock ngắn cho transition, giải phóng lock trước khi chạy code/test, và từ chối mọi path cấu hình đi ra ngoài repository.

### Mô hình dispatch

Supervisor chọn task `planned` đã hoàn tất dependency. Worker phải available, chưa vượt `max_active`, khớp agent/capability và không trùng active writer scope. Dispatch ghi assignment vào mailbox và prompt vào outbox, rồi chuyển task thành `assigned`.

Worker dùng `worker pull` hoặc `task claim` để chuyển sang `in_progress`, chỉ sửa trong scope đã claim và chỉ nộp bằng `task report` sau khi activation. Lệnh report cập nhật report inbox, file của agent, completed log toàn cục, report index và handover của task.

### Production gate

Mặc định phải có evidence lặp lại cho acceptance, QA focused/integration pass, không còn finding P0/P1 và có operational/rollback notes. CLI không tự deploy; side effect bên ngoài luôn cần prompt cấp trên cho phép.
