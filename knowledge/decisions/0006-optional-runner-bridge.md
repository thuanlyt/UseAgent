# ADR-0006: Optional bounded worker runner bridge

- `Status`: accepted
- `Date`: 2026-09-04
- `Owner`: supervisor

## Context

The file protocol already dispatches work and generates copyable prompts, but a
user who wants automatic worker intake still has to manually start every
runtime. Codex, Claude Code and Antigravity do not share a stable launch API,
and a hidden model-specific daemon would break portability and safety.

## Decision

Keep manual `worker pull` as the zero-configuration path and add an explicit
optional runner object to an agent registration. The runner is an argv list,
not a shell string, and must receive `{assignment_path}`. `worker run` claims
the oldest assigned task, invokes the configured adapter from the project root,
enforces a timeout and a finite task/idle budget, records bounded output as
evidence, and requires the adapter to submit `task report`. If the adapter
fails or exits without a report, UseAgent writes a failed worker report rather
than leaving a task silently stuck in `in_progress`.

The adapter owns provider-specific flags, authentication and process sandboxing.
UseAgent does not invent Codex/Claude/Antigravity commands or launch a runner
unless the project owner explicitly configured one.

## Alternatives rejected

- A hidden daemon or infinite watch loop would violate bounded autopilot and
  make external side effects difficult to audit.
- A vendor-specific adapter in the core would make the file contract less
  portable and would require credentials/dependencies.
- Automatically marking work done after process exit would bypass the report,
  review and QA gates.

## Consequences

- A configured local adapter can make worker intake hands-off for a finite run.
- Mixed runtimes share one contract while keeping their launch details isolated.
- Manual sessions and runtimes without a CLI remain fully supported.
- The configured adapter is trusted code; the core guarantees process
  invocation semantics and state/report gates, not model sandboxing.

## Evidence / source anchors

- `tools/useagent.py:runner_settings`
- `tools/useagent.py:cmd_worker_run`
- `tests/test_useagent.py:UseAgentCliTests.test_worker_run_invokes_runner_and_accepts_automatic_report`
- `examples/multi-runtime-conformance/run_conformance.py:simulated_runner_args`
