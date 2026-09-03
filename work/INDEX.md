# Work ledger

`work/registry.json` là registry máy đọc được. `work/items/<id>.md` chứa mục tiêu, scope, acceptance, handover và event log. `work/agents/<agent>/` là mailbox assignment/report/completed của từng worker. `work/evidence/` giữ output dài; `work/checkpoints/` giữ điểm resume.

## Lifecycle

`planned -> assigned -> in_progress -> reported -> needs_review -> done`.

Task có thể chuyển `blocked` khi thiếu thông tin/dependency và `cancelled` khi mục tiêu không còn tồn tại. Không dùng `done` để biểu thị “đã thử”; phải có evidence.

## Cách lấy context

```powershell
python tools/useagent.py context
python tools/useagent.py context --task UA-0001
python tools/useagent.py task list --status in_progress
```

Không chỉnh `registry.json` bằng tay trong workflow bình thường. CLI dùng lock file và ghi nguyên tử để các agent không làm hỏng state khi claim/update gần nhau.

## Supervisor loop

```powershell
python tools/useagent.py agent register --id frontend --role worker --scope app/frontend
python tools/useagent.py supervisor cycle
python tools/useagent.py worker pull --agent frontend
python tools/useagent.py task report UA-0001 --agent frontend --result completed --summary "..." --next-action "Review"
python tools/useagent.py supervisor cycle --run-qa
```

Supervisor đọc `work/SUPERVISOR_REPORT.md`, report inbox và `work/completed/COMPLETED.md`, sau đó dispatch task ready vào mailbox và tạo prompt trong `work/outbox/`.
