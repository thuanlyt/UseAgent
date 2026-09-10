# Project brief

Đây là nơi `$relwit` lưu bản tóm tắt bền vững được rút ra từ prompt ban đầu và các quyết định đã được chấp nhận.

- `goal`: Cung cấp một lớp evidence và release-assurance nằm trong repository cho workflow lập trình bằng AI; supervisor, DAG, mailbox và autopilot là capability điều phối nhẹ tùy chọn.
- `definition_of_done`: Repository lưu evidence provenance, output bounded/sanitized, source-bound QA, review verification và Git release durability; người dùng có thể trỏ CLI vào project bên ngoài; tài liệu song ngữ, governance, CI và MIT license phản ánh đúng trust model; không tự deploy khi chưa được phép.
- `constraints`: Dependency-free local CLI; runtime state được tạo local trong project sau `init`; trusted-local/repository, không phải OS sandbox hay distributed orchestrator; không worktree manager, registry migration, provider quota/auth backlog hoặc feature ngoài freeze; không deploy, xóa dữ liệu, đổi secret/quyền hoặc gọi external service nếu chưa được prompt cho phép.
- `selected_stack`: Python 3.11+ standard library cho CLI/tests; JSON cho state/config; Markdown cho knowledge/work/mailbox/report; TOML cho Codex agent profiles; Git/GitHub Actions cho versioning và CI.
- `last_updated`: 2026-09-07
- `owner`: supervisor

Không dùng file này để thay thế acceptance criteria của work item. Mỗi assumption về tech stack phải có decision/source anchor tương ứng trong `knowledge/decisions/`.
