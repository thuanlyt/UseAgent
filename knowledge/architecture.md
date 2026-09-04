# UseAgent architecture

## Ý tưởng trung tâm

UseAgent không cố biến nhiều agent thành nhiều process cùng ghi tự do. Nó cung cấp một control plane nhỏ gồm instruction, skill, knowledge ledger, work ledger và checkpoint. Shared folder là nơi các agent nhìn cùng một nguồn sự thật; quyền ghi được phân phối theo work item và scope.

```text
User goal
   |
   v
Orchestrator -> work/registry.json -> scoped workers
      |                |                 |
      v                v                 v
knowledge/        locks + claims     code/tests
      |                                  |
      +---------- reviewer/evidence <----+
                         |
                         v
              checkpoint -> next safe cycle
```

## Sáu lớp

1. **Durable instructions** — `AGENTS.md` chứa invariant áp dụng cho mọi agent.
2. **Reusable workflows** — `.agents/skills/*/SKILL.md` chỉ giữ logic quyết định và link đến reference khi cần.
3. **Role agents** — `.codex/agents/*.toml` giới hạn nhiệm vụ, model/sandbox có thể kế thừa parent.
4. **Knowledge ledger** — `knowledge/` giữ map, contract, module card và quyết định; mỗi entry nên có source anchor.
5. **Work ledger** — `work/registry.json` là trạng thái máy đọc được; `work/items/*.md` là hồ sơ người đọc được; `work/agents/`, `work/reports/` và `work/outbox/` là mailbox/report protocol.
6. **Quality gates** — evidence, review, checkpoint và điều kiện dừng biến tiến độ thành thứ có thể kiểm tra.

## Cấp độ công việc

| Level | Phạm vi | Hình thức phối hợp | Điều kiện hoàn tất |
| --- | --- | --- | --- |
| L0 | Một chỉnh sửa nhỏ, một file | Một worker + focused test | Diff nhỏ, evidence rõ |
| L1 | Một task kỹ thuật qua vài file | Explorer rồi worker rồi reviewer | Acceptance + regression evidence |
| L2 | Feature/module | DAG nhiều task, tối đa một writer mỗi scope | Contract/module card cập nhật |
| L3 | Milestone liên module | Planner, nhóm worker độc lập, release gate | Integration, risk list, checkpoint |
| L4 | Production outcome | Chuỗi milestone, autopilot theo vòng | Release criteria, vận hành, rollback và phê duyệt |

Không tăng level chỉ vì có nhiều file. Tăng level khi dependency, owner, gate hoặc rủi ro vận hành thay đổi.

## Trạng thái task

`planned -> assigned -> in_progress -> reported -> needs_review -> done`.

Nhánh ngoại lệ: `planned/assigned/in_progress/reported -> blocked`, hoặc `planned -> cancelled`. Task chỉ dispatch/claim được khi dependency đã `done` và scope không xung đột với writer active. `reported` là worker đã gửi report; `done` cần review và ít nhất một evidence có thể lặp lại. `done` và `cancelled` là terminal states, không được reopen bằng `task update`.

## Quy tắc chia việc

- Chia theo boundary có thể kiểm tra: module, API contract, test surface, migration hoặc runbook.
- Tách read-heavy discovery khỏi write-heavy implementation.
- Hai task chỉ chạy song song khi không sửa cùng path/subtree và không cạnh tranh cùng external resource.
- Một task chỉ có một writer chính; reviewer không sửa code.
- Handover trả summary ngắn, không trả raw transcript.

## Kho tri thức tiết kiệm token

Module card tối thiểu nên ghi: trách nhiệm, entry points, public interfaces, dependency edges, test commands, các invariant và source anchors. Card không sao chép implementation. Khi card stale, agent đọc đúng file bị ảnh hưởng rồi cập nhật card; không biến card thành nguồn sự thật thay thế code.

## Các phương án bị loại

- **Một mega-skill**: description và instruction phình to, kích hoạt sai và làm mọi task mang theo context không liên quan.
- **Nhiều writer cùng file**: tạo race, merge conflict và không xác định owner.
- **Chỉ dùng Markdown tự do**: người đọc được nhưng khó kiểm tra dependency, claim và trạng thái.
- **Cho autopilot tự sửa không có gate**: dễ drift khỏi mục tiêu và lặp lỗi.
- **Quét full repository ở mỗi vòng**: tốn token và làm chìm tín hiệu trong log.
- **Dùng memory thay cho project state**: không tái lập được giữa agent/thread và có thể stale.

## Invariant quan trọng

1. Registry là state machine; mọi transition phải qua CLI có lock.
2. Knowledge là index có dẫn nguồn, không phải bản copy của code.
3. Parallelism được tối ưu ở đọc/kiểm tra; ghi được serialized theo scope.
4. Supervisor/autopilot luôn làm một vòng hữu hạn rồi checkpoint; scheduler chỉ gọi lại vòng đó.
5. Production gate không tự cấp quyền deploy.
