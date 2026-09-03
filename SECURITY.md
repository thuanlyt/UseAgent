# Security policy / Chính sách bảo mật

## English

UseAgent is a local coordination tool. It can write files inside the configured repository and execute only the QA commands explicitly configured by the project. It does not grant deployment, credential or external-service authority.

Please do not open a public issue for a suspected secret leak, path traversal, command execution flaw or permission bypass. Report it privately to the repository owner through GitHub's private vulnerability reporting when enabled, or contact the maintainer before disclosure. Include a minimal reproduction, affected version/commit and impact. Do not attach live credentials.

Maintainers will acknowledge reports, reproduce them in an isolated copy, patch the smallest safe surface, add a regression test where practical and publish a coordinated fix.

## Tiếng Việt

UseAgent là công cụ điều phối local. Nó chỉ ghi file trong repository đã cấu hình và chỉ chạy QA command do dự án khai báo. Nó không tự cấp quyền deploy, credential hoặc dịch vụ bên ngoài.

Không mở issue công khai cho lỗi lộ secret, path traversal, command execution hoặc bypass quyền. Hãy báo riêng cho maintainer qua private vulnerability reporting của GitHub nếu đã bật, hoặc liên hệ maintainer trước khi công bố. Gửi reproduction tối thiểu, version/commit bị ảnh hưởng và impact; không gửi credential thật.
