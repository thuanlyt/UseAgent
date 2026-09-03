# Agent mailboxes

Mỗi agent đã đăng ký có một thư mục riêng:

- `INBOX.md`: assignment prompt do supervisor phát hành.
- `REPORT.md`: báo cáo ngắn của agent.
- `COMPLETED.md`: task agent đã báo hoàn tất, vẫn có thể chờ review/QA.
- `inbox/`: assignment đầy đủ cho từng task.

Dùng `python tools/useagent.py agent register ...` để tạo mailbox; không tự đổi tên các file được cấu hình.
