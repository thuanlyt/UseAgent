# ADR-0004: Mailbox Markdown cho worker và supervisor

- **Status:** accepted
- **Date:** 2026-09-04

## Decision

UseAgent phát hành task vào mailbox Markdown cấu hình trong `useagent.config.json`, nhận report qua `task report`, rồi gom vào report trung tâm và completed log.

## Why

Agent khác nhau có thể không dùng cùng runtime/thread. File Markdown là giao thức đơn giản, inspectable và dễ gửi lại dưới dạng prompt; registry JSON vẫn giữ state máy đọc được.

## Consequences

- Cần đăng ký roster agent trước khi dispatch.
- File `.md` không đủ để bảo đảm worker chạy; worker phải được Codex/runtime gọi hoặc người dùng gửi assignment prompt.
- Report completed vẫn phải qua review/QA trước production.
