# UseAgent project instructions

## Mục tiêu vận hành

Đây là một workspace điều phối nhiều agent. Giữ main agent tập trung vào yêu cầu, quyết định và tổng hợp; đẩy việc đọc nặng, kiểm thử và review sang agent chuyên trách.

Khi người dùng chỉ cung cấp goal và roster, dùng `$useagent` làm front door. Supervisor ghi project brief, chọn/ghi rõ stack assumption, tạo DAG, dispatch mailbox và theo dõi cho đến production gate.

## Quy tắc bắt buộc

1. Trước khi đọc code, đọc `knowledge/INDEX.md` và `work/registry.json`. Chỉ mở module card, contract, decision và file code liên quan đến task.
2. Mọi thay đổi phải thuộc một work item có `id`, acceptance criteria, scope và owner. Dùng `python tools/useagent.py` để tạo/dispatch/claim/report/cập nhật thay vì sửa registry bằng tay.
3. Supervisor dispatch task ready vào mailbox `work/agents/<agent>/INBOX.md` và prompt đầy đủ vào `work/outbox/`. Worker pull task rồi mới sửa. Một path hoặc subtree chỉ có tối đa một writer đang ở `assigned`/`in_progress`; agent đọc có thể chạy song song.
4. Không dùng tóm tắt cũ như sự thật nếu thiếu source anchor. Khi behavior, contract hoặc cấu trúc thay đổi, cập nhật knowledge card và ghi decision nếu cần.
5. Worker chỉ sửa trong scope đã claim. Khi hoàn tất, dùng `task report` để ghi vào mailbox `REPORT.md`, report inbox và `COMPLETED.md`; không tự đánh dấu `done` nếu chưa review.
6. Reviewer phải đưa evidence có thể lặp lại: command, kết quả, file/line và rủi ro còn lại. Supervisor đọc report, chạy QA đã cấu hình, tạo debug task khi fail và chỉ đóng task sau gate.
7. Mỗi vòng làm việc dài phải có checkpoint: đã làm gì, blocker, next action và điều kiện dừng. Dừng khi acceptance mơ hồ, quyền truy cập thiếu, conflict scope hoặc lỗi lặp lại chưa có giả thuyết mới.
8. Không deploy, xóa dữ liệu, thay đổi secret/quyền truy cập hoặc gọi dịch vụ ngoài phạm vi prompt nếu chưa được người dùng cho phép. Scheduler có thể gọi lại cycle, nhưng không được biến cycle thành loop vô hạn.

## Luồng mặc định

`context -> plan/DAG -> dispatch -> worker pull -> implement -> report .md -> review/QA -> evidence -> knowledge update -> checkpoint -> next cycle`.

Đối với task độc lập, có thể dùng subagent song song. Đối với task cùng file, tuần tự hóa bằng scope hoặc dùng Git worktree; không cho nhiều writer cùng sửa một working tree mà không có owner rõ ràng.

## Handover tối thiểu

Mọi handover phải nêu: task id, trạng thái, file đã chạm, command đã chạy, evidence, blocker và bước tiếp theo. Chỉ gửi summary ngắn có đường dẫn; không dán toàn bộ log nếu không cần.
