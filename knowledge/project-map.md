# Project map

`freshness: verified` — updated 2026-09-06 after adding the OSBlog dogfood
case study, capture manifest and docs-site case-study route.

## Topology

| Path | Trách nhiệm | Agent nên đọc khi |
| --- | --- | --- |
| `AGENTS.md` | Luật chung | Mọi task |
| `.agents/skills/relwit/` | Supervisor front door | Người dùng chỉ đưa goal + roster |
| `.agents/skills/` | Workflow reusable | Task khớp skill |
| `.codex/agents/` | Vai trò agent | Spawn/custom agent |
| `knowledge/` | Context ledger | Trước khi đọc code |
| `knowledge/project-brief.md` | Goal/DOD/constraints/stack assumptions | Bootstrap supervisor |
| `work/` | Runtime task/evidence/checkpoint được `init` tạo local | Bật optional supervision trong project |
| `relwit.config.json` | Roster, mailbox path, QA và production gates | Setup supervisor |
| `relwit/cli.py` | State CLI/validator | Tạo claim/update/checkpoint |
| `pyproject.toml`, `tools/__init__.py` | Installable `relwit` console package | Cài CLI hoặc kiểm tra release |
| `templates/` | Mẫu hồ sơ | Tạo artifact mới |
| `docs/` | Tài liệu onboarding, vận hành và evidence case study | Setup, provider walkthrough, autopilot, dogfood findings and capture provenance |
| `docs-site/` | Static bilingual documentation website | Build, content and hosting QA |
| `docs-site/assets/` | Local hero illustration and explanatory SVG diagrams | Visual docs, social preview and image integrity QA |
| `.github/` | CI, issue forms và pull-request template | Đóng góp hoặc release |
| `README.md` | Public overview, bilingual quick start và contracts | Onboarding |
| `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` | Open-source governance | Phát hành hoặc đóng góp |
| `tests/` | Regression cho control plane | Sửa tools hoặc schema |

## Runtime entry points

- `relwit context`: snapshot context ngắn.
- `relwit task ...`: tạo và chuyển trạng thái work item.
- `relwit checkpoint create ...`: tạo durable handover.
- `relwit supervisor cycle`: ingest report, dispatch worker, QA tùy chọn và tạo supervisor report/checkpoint.
- `relwit worker pull --agent <id>` / `task report ...`: nhận assignment và gửi report vào các file Markdown cấu hình.
- `relwit worker run --agent <id>`: bounded opt-in runner tự pull/gọi adapter và lưu runner evidence.
- `python examples/multi-runtime-conformance/run_conformance.py`: credential-free routing and pull/report/ingest/QA conformance for Codex, Claude Code and Antigravity-style identities.
- `relwit validate`: kiểm tra layout, registry, skills và agent TOML.
- `python -m unittest discover -s tests -v`: kiểm tra CLI và state transitions.
- `python -m pip install --no-deps .` / `relwit validate`: smoke test package entry point.
- `.github/workflows/ci.yml`: lặp lại compile, unit test và protocol validation trên Python 3.11–3.13.
- `docs/getting-started.md`: hands-on onboarding, provider/runtime matrix and Codex + Claude Code + Antigravity walkthrough.
- `docs/case-study-osblog.md`: evidence-frozen OSBlog dogfood timeline, findings and ReleaseWitness improvement priorities.
- `docs/evidence/osblog-dogfood-capture-manifest.md`: curated/local/blocked media classification and privacy checklist.
- `docs-site/assets/*.svg` / `relwit-control-plane-hero.webp`: source-owned diagrams and optimized hero visual; keep alt text/dimensions in consuming HTML.

## Code ownership hiện tại

- `relwit/cli.py`: control-plane worker; thay đổi cần test CLI.
- `.agents/skills/`: skill authoring; thay đổi cần `quick_validate.py`.
- `knowledge/`, `work/`, `docs/`, `templates/`: documentation/state; thay đổi cần `validate`.
