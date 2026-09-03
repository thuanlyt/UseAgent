# ADR-0003: Autopilot theo vòng hữu hạn

- **Status:** accepted
- **Date:** 2026-09-03

## Decision

Autopilot thực hiện một cycle: đọc context, chọn task ready, claim/dispatch, review, cập nhật knowledge, tạo checkpoint rồi kết thúc hoặc nêu next action.

## Why

Vòng hữu hạn có thể audit và resume; loop vô hạn không có completion criteria, dễ tiêu token và drift khỏi production goal.

## Stop conditions

Acceptance mơ hồ, thiếu quyền, scope conflict, external dependency chưa sẵn sàng, lỗi lặp lại sau ba giả thuyết hợp lý, hoặc bước tiếp theo có destructive/external impact chưa được cho phép.
