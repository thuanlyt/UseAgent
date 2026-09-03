# Contributing to UseAgent / Đóng góp cho UseAgent

## English

Thank you for improving the supervisor protocol. Keep changes small, explicit and reproducible.

### Before changing files

1. Read `AGENTS.md`, `knowledge/INDEX.md` and `work/registry.json`.
2. Create or claim a work item with an id, owner, scope and acceptance criteria.
3. Check that no other active writer owns the same path or subtree.
4. Record architecture or protocol changes in `knowledge/decisions/` and refresh the relevant map/card.

### Development loop

```powershell
python tools/useagent.py validate
python -m unittest discover -s tests -v
python -m py_compile tools/useagent.py tests/test_useagent.py
```

Use `apply_patch` or an equivalent reviewable edit, keep the CLI dependency-free, and report the exact commands and results. A worker handover must include task id, status, files touched, evidence, blocker and next action. Do not mark a task `done` merely because implementation is complete; review owns that gate.

Pull requests should explain the contract change, compatibility impact, test evidence and any remaining risk. Do not include secrets, generated runtime state, private prompts or machine-specific paths.

## Tiếng Việt

Cảm ơn bạn đã cải thiện giao thức supervisor. Giữ thay đổi nhỏ, rõ phạm vi và có thể tái hiện.

Trước khi sửa, đọc `AGENTS.md`, `knowledge/INDEX.md`, `work/registry.json`; tạo/claim work item có id, owner, scope, acceptance; kiểm tra không có writer khác cùng scope; nếu đổi kiến trúc/contract thì cập nhật decision và knowledge map.

Chạy `python tools/useagent.py validate`, `python -m unittest discover -s tests -v` và `python -m py_compile tools/useagent.py tests/test_useagent.py`. Handover phải có task id, trạng thái, file, evidence, blocker và next action. Không đưa secret, runtime state cá nhân hoặc path máy vào pull request.
