# UseAgent operations

## Install the CLI

UseAgent can run directly from a checkout, or as an installed console command:

```powershell
python -m pip install --no-deps .
useagent --help
useagent validate
```

The installed command uses the current directory as its default project root.
To operate on another prepared repository, pass the root before the command:

```powershell
useagent --root F:\dev\DemoStore validate
useagent --root F:\dev\DemoStore supervisor cycle --run-qa
```

The package has no runtime dependencies. Python 3.11 or newer is required;
the build backend is used only during installation.

## Tạo task

```powershell
python tools/useagent.py task new `
  --title "Implement feature X" `
  --level L1 `
  --owner worker `
  --scope src/backend/x.py tests/test_x.py `
  --acceptance "Behavior X works" `
  --acceptance "Focused regression test passes"
```

Task được tạo ở `planned`. Planner nên tách dependency trước khi giao worker.

## Đăng ký worker và tự dispatch

```powershell
python tools/useagent.py agent register --id backend --role worker --scope src/backend --scope tests --capability python
python tools/useagent.py agent register --id frontend --role worker --scope src/frontend --scope tests --capability web
python tools/useagent.py supervisor cycle
```

`supervisor cycle` tìm task ready, tự chọn worker còn rảnh theo scope/capability, ghi assignment vào `work/agents/<id>/inbox/`, cập nhật `INBOX.md`, và tạo prompt gửi ngoài phiên tại `work/outbox/`. Nếu Codex có subagent runtime, supervisor nên spawn worker trực tiếp; nếu không, gửi file outbox cho agent tương ứng.

Có thể chỉ định file Markdown riêng cho từng worker:

```powershell
python tools/useagent.py agent register --id qaagent --directory work/qaagent `
  --inbox-file work/mail/qa-inbox.md `
  --report-file work/mail/qa-report.md `
  --completed-file work/mail/qa-completed.md
```

## Claim và thực thi

```powershell
python tools/useagent.py worker pull --agent backend
python tools/useagent.py context --task UA-0001
python tools/useagent.py task report UA-0001 --agent backend --result completed --summary "Implementation complete" --next-action "Review and QA" --file src/backend/x.py --check "python -m unittest: pass"
python tools/useagent.py supervisor cycle --run-qa
```

Worker report tự ghi vào `work/agents/backend/REPORT.md`, `work/reports/inbox/`, `work/reports/REPORTS.md` và `work/completed/COMPLETED.md`. Reviewer kiểm tra diff và evidence, sau đó cập nhật `needs_review`/`done`. `completed` trong log chỉ là worker đã báo xong, không phải production-ready.

## Parallelism

- Explorer, test analyst và docs analyst có thể chạy song song nếu read-only.
- Worker chỉ chạy song song khi `scope` không giao nhau.
- Nếu task cần cùng file, dependency phải tuần tự hoặc mỗi nhánh dùng Git worktree.
- `work/.state.lock` chỉ rất ngắn cho state transition; không giữ lock trong lúc chạy test hay sửa code.

## Supervisor cycle và QA

```powershell
python tools/useagent.py supervisor ingest
python tools/useagent.py supervisor report
python tools/useagent.py supervisor qa
python tools/useagent.py supervisor cycle --retry-blocked --run-qa
```

Khai báo `supervisor.qa_commands` dạng mảng command string trong `useagent.config.json` để CLI chạy test/lint/build đã được project cho phép:

```json
{
  "supervisor": {
    "qa_commands": [
      "python -m unittest discover -s tests -v",
      "python tools/useagent.py validate"
    ]
  }
}
```

Output dài được lưu thành evidence; cycle sẽ chỉ ra task report, task blocked, worker đang active và next action.

## Handover

Tóm tắt bằng task id, trạng thái, file, command/evidence, blocker và next action. Worker dùng `task report`; supervisor dùng `work/SUPERVISOR_REPORT.md` và checkpoint. Ghi report dài vào `work/evidence/` và đặt path trong task.

## Kiểm tra toàn hệ thống

```powershell
python tools/useagent.py validate
python -m unittest discover -s tests -v
```

## Quyền và side effects

Skill chỉ điều phối workflow. Các hành động deploy, migration destructive, thay đổi secret, gọi connector hoặc mở rộng quyền phải được prompt cấp trên cho phép riêng.
