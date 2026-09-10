# Orchestration reference

## Level guide

- **L0:** one small edit and one focused check; no delegation unless context is unknown.
- **L1:** one bounded technical task; explorer -> worker -> reviewer.
- **L2:** feature/module; create a DAG with separate contracts, implementation and tests.
- **L3:** milestone; parallelize independent work, then run integration and release gate.
- **L4:** production outcome; repeat L3 cycles with operational, rollback and approval gates.

## Work item shape

Every item needs: objective, level, owner, exact path/subtree scope, acceptance criteria, dependencies, verification command and handover format. If one of these is unknown, keep the item `planned` or `blocked`.

## Recommended DAG

```text
discovery (read-only)
        |
contract/design ---- test plan
        |                 |
implementation ---------+
        |
focused verification -> review -> knowledge update -> checkpoint
```

Only nodes with no unfinished dependency may be claimed. Two write nodes may be concurrent only when their scopes do not overlap.

## Agent prompt contract

Tell each subagent: task id, role, allowed scope, files it may touch, inputs to read, expected output, whether to wait for siblings, and stop conditions. Ask for a summary with paths and evidence, not transcript.
