# UseAgent implementation roadmap

Đây là roadmap cấp L3/L4 mẫu; task thật được tạo trong `work/registry.json`.

## M0 — Control plane (L0/L1)

- CLI tạo/claim/update task.
- Validator cho state, scope conflict, skill và custom agent.
- Unit tests cho các transition chính.

## M1 — Context ledger (L1/L2)

- Module card có source anchor và freshness.
- Contract/decision index.
- Context snapshot theo task với giới hạn ký tự.

## M2 — Delivery workflow (L2/L3)

- Planner tạo DAG theo level.
- Worker/reviewer handover bằng evidence.
- Release gate kiểm tra acceptance, regression và rollback note.

## M3 — Production autopilot (L3/L4)

- Checkpoint/resume không mất state.
- Prompt scheduled task phù hợp với local project/worktree.
- Review các run đầu, chỉnh cadence, giữ điều kiện dừng và quyền deploy ở ngoài skill.
