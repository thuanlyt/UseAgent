# Project map

`freshness: verified` — updated 2026-09-04 after adding the public architecture guide and GitHub release files.

## Topology

| Path | Trách nhiệm | Agent nên đọc khi |
| --- | --- | --- |
| `AGENTS.md` | Luật chung | Mọi task |
| `.agents/skills/useagent/` | Supervisor front door | Người dùng chỉ đưa goal + roster |
| `.agents/skills/` | Workflow reusable | Task khớp skill |
| `.codex/agents/` | Vai trò agent | Spawn/custom agent |
| `knowledge/` | Context ledger | Trước khi đọc code |
| `knowledge/project-brief.md` | Goal/DOD/constraints/stack assumptions | Bootstrap supervisor |
| `work/` | Task/evidence/checkpoint | Lập kế hoạch hoặc handover |
| `useagent.config.json` | Roster, mailbox path, QA và production gates | Setup supervisor |
| `tools/useagent.py` | State CLI/validator | Tạo claim/update/checkpoint |
| `templates/` | Mẫu hồ sơ | Tạo artifact mới |
| `docs/` | Tài liệu onboarding và vận hành | Setup, provider walkthrough, autopilot |
| `.github/` | CI, issue forms và pull-request template | Đóng góp hoặc release |
| `README.md` | Public overview, bilingual quick start và contracts | Onboarding |
| `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` | Open-source governance | Phát hành hoặc đóng góp |
| `tests/` | Regression cho control plane | Sửa tools hoặc schema |

## Runtime entry points

- `python tools/useagent.py context`: snapshot context ngắn.
- `python tools/useagent.py task ...`: tạo và chuyển trạng thái work item.
- `python tools/useagent.py checkpoint create ...`: tạo durable handover.
- `python tools/useagent.py supervisor cycle`: ingest report, dispatch worker, QA tùy chọn và tạo supervisor report/checkpoint.
- `python tools/useagent.py worker pull --agent <id>` / `task report ...`: nhận assignment và gửi report vào các file Markdown cấu hình.
- `python tools/useagent.py validate`: kiểm tra layout, registry, skills và agent TOML.
- `python -m unittest discover -s tests -v`: kiểm tra CLI và state transitions.
- `.github/workflows/ci.yml`: lặp lại compile, unit test và protocol validation trên Python 3.11–3.13.
- `docs/getting-started.md`: hands-on onboarding, provider/runtime matrix and Codex + Claude Code + Antigravity walkthrough.

## Code ownership hiện tại

- `tools/useagent.py`: control-plane worker; thay đổi cần test CLI.
- `.agents/skills/`: skill authoring; thay đổi cần `quick_validate.py`.
- `knowledge/`, `work/`, `docs/`, `templates/`: documentation/state; thay đổi cần `validate`.
