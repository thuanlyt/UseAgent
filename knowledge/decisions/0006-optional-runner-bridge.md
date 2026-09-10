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
fails or exits without a report, ReleaseWitness writes a failed worker report rather
than leaving a task silently stuck in `in_progress`.

The adapter owns provider-specific flags, authentication and process sandboxing.
ReleaseWitness does not invent Codex/Claude/Antigravity commands or launch a runner
unless the project owner explicitly configured one. A runner may optionally
declare an argv-only, bounded `preflight` command. The core recognizes only
the machine-readable readiness states `ready`, `unavailable`,
`misconfigured`, `no_target` and `unknown`; `ready` is prerequisite evidence,
not a quota prediction.

Started adapters may emit a complete `relwit_runtime_result` JSON envelope.
ReleaseWitness normalizes its failure class and recommended finite disposition. The
`quota_limited` and `auth_error` classes require `authoritative: true`; prose
in stdout/stderr cannot establish either condition. A pre-start failure keeps
the task assigned and records bounded runtime evidence, while a failure after
pull uses the existing automatic failed-report safeguard.

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
- Static dispatch checks prevent clearly malformed or unavailable configured
  runners from receiving new work; missing preflight remains an explicit
  unknown compatibility mode for existing adapters.
- Readiness output is local/runtime data first; only normalized metadata and a
  local spool reference are attached to the task, preserving source-bound QA.
- The configured adapter is trusted code; the core guarantees process
  invocation semantics and state/report gates, not model sandboxing.

## Evidence / source anchors

- `relwit/cli.py:runner_settings`
- `relwit/cli.py:cmd_worker_run`
- `tests/test_relwit.py:RelWitCliTests.test_worker_run_invokes_runner_and_accepts_automatic_report`
- `examples/multi-runtime-conformance/run_conformance.py:simulated_runner_args`
