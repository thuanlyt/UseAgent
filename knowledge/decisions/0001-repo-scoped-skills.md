# ADR-0001: Repo-scoped skills và state trong repository

- **Status:** accepted
- **Date:** 2026-09-03

## Decision

Đặt skill dùng chung tại `.agents/skills/`, custom agent tại `.codex/agents/`, knowledge tại `knowledge/` và work state tại `work/`.

## Why

Skill repo-scoped được commit cùng project nên agent khác có thể dùng đúng workflow. State nằm trong project giúp khôi phục sau khi đổi thread/máy và tránh phụ thuộc vào trí nhớ của một agent.

## Consequences

- Mọi người cần mở đúng project root để Codex tự phát hiện skill.
- Skill chỉ chứa workflow; dữ liệu thay đổi nằm trong ledger của project.
- Nếu cần phân phối ra ngoài project, có thể đóng gói thành plugin ở giai đoạn sau.
