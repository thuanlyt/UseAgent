# Worker reference

## Before editing

- Confirm the task exists and is not already owned by another active writer.
- Confirm dependency tasks are `done`.
- Confirm every intended path is inside scope.
- Record a short implementation plan if the change crosses a boundary.

## After editing

- Run focused verification before broad suites.
- Add evidence as `kind=value`; include command and result.
- List changed files and note knowledge/contract updates.
- Move to `needs_review`, not `done`, unless the parent workflow explicitly combines review and completion.

## Block instead of guessing

Use `blocked` when acceptance, dependency, permission, or ownership is unclear. Include the exact question and the smallest decision needed to resume.
