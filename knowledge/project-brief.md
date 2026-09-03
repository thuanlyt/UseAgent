# Project brief

Đây là nơi `$useagent` lưu bản tóm tắt bền vững được rút ra từ prompt ban đầu và các quyết định đã được chấp nhận.

- `goal`: Cung cấp một supervisor skill và file-first control plane để một model điều phối nhiều agent trong cùng repository, tự tạo/dispatch/claim/report/review/QA/checkpoint và hướng dự án đến production gate.
- `definition_of_done`: Người dùng chỉ cần đưa goal nhẹ và roster; supervisor lập roadmap/DAG; worker nhận task từ mailbox; report/completed/evidence được ghi vào Markdown; supervisor ingest, QA, debug, review và checkpoint theo cycle hữu hạn; repository có tài liệu song ngữ, governance, CI, MIT license và không tự deploy khi chưa được phép.
- `constraints`: Dependency-free local CLI; mọi task có scope/owner/acceptance/evidence; một active writer mỗi scope; path không được ra ngoài repository; không deploy, xóa dữ liệu, đổi secret/quyền hoặc gọi external service nếu chưa được prompt cho phép; autopilot phải hữu hạn và có điều kiện dừng.
- `selected_stack`: Python 3.11+ standard library cho CLI/tests; JSON cho state/config; Markdown cho knowledge/work/mailbox/report; TOML cho Codex agent profiles; Git/GitHub Actions cho versioning và CI.
- `last_updated`: 2026-09-04
- `owner`: supervisor

Không dùng file này để thay thế acceptance criteria của work item. Mỗi assumption về tech stack phải có decision/source anchor tương ứng trong `knowledge/decisions/`.
