# ADR-0002: Một writer cho mỗi scope

- **Status:** accepted
- **Date:** 2026-09-03

## Decision

Chỉ task ở `claimed` hoặc `in_progress` mới được xem là writer active. Claim sẽ từ chối khi scope exact hoặc subtree giao nhau với writer khác.

## Why

Shared working tree không cung cấp merge semantics cho hai agent đang sửa cùng path. Scope claim tạo owner rõ ràng và giữ parallelism ở những phần độc lập.

## Consequences

- Task lớn phải tách boundary trước khi spawn.
- Khi cần hai hướng code song song, dùng Git worktree rồi merge qua reviewer/gate.
- Lock của CLI chỉ bảo vệ state transition; nó không thay thế scope discipline.
