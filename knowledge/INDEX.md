# UseAgent context index

Đây là điểm vào bắt buộc cho mọi agent. Mục tiêu của index là giúp agent biết phải đọc gì, không phải chứa toàn bộ kiến thức.

## Đọc theo thứ tự

1. `AGENTS.md` — luật vận hành và phạm vi an toàn.
2. `$useagent` — supervisor front door; dùng các skill chuyên trách khi cần.
3. `knowledge/architecture.md` — mô hình điều phối, cấp độ công việc và invariant.
4. `knowledge/project-brief.md` — goal, definition of done, constraints và stack assumption.
5. `knowledge/project-map.md` — cây thư mục và entry point hiện tại.
6. Module card liên quan trong `knowledge/modules/`.
7. Contract liên quan trong `knowledge/contracts/` và decision mới nhất trong `knowledge/decisions/`.
8. Work item cụ thể trong `work/items/`.

## Nguồn sự thật

- Cấu trúc/chức năng: file code thực tế và module card có source anchor.
- Trạng thái công việc: `work/registry.json`, sau đó là hồ sơ Markdown tương ứng.
- Quy tắc phối hợp: `AGENTS.md` và skill đang được gọi.
- Roster/mailbox: `useagent.config.json` và `work/agents/`.
- Quyết định kiến trúc: `knowledge/decisions/`.

## Quy tắc tiết kiệm context

- Bắt đầu bằng file này, không chạy lệnh đọc đệ quy toàn repository.
- Dùng `python tools/useagent.py context --task <id>` để lấy snapshot ngắn.
- Chỉ đọc module card và file code nằm trong scope/dependency của task.
- Log dài phải được lưu trong evidence; handover chỉ giữ kết luận, command và đường dẫn.
- Khi map không còn đúng, sửa map trong cùng task và ghi `updated_at`/source anchor.

## Tình trạng index

- `freshness`: verified
- `last_verified`: 2026-09-04
- `owner`: planner/release_gate
- `next_refresh`: sau khi thêm module, public contract, build command hoặc deploy path; visual asset contract hiện được ghi tại `knowledge/decisions/0007-visual-documentation-system.md`.
