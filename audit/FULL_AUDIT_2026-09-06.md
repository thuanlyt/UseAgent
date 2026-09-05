# UseAgent — Full repository audit

**Audit date:** 2026-09-06 (UTC+7)  
**Audited remote:** `thuanlyt/UseAgent` → `main`  
**Snapshot commit:** `0fd2244d68b8429213f0cbc6d7beaeb916f37620` (`chore: add UseAgent workflow demo media`)  
**Audit mode:** read-only static repository review + GitHub CI/status evidence. No application/source file outside `audit/` was modified by this audit.

> Important: this is a snapshot audit of the code that was actually pushed to GitHub. The attached Codex screenshot shows a newer local/in-progress session (including UA-0088/UA-0089 and OSBlog-related security work), but those task IDs/files are not present on remote `main` at the snapshot above. Therefore this report does **not** treat uncommitted or unpushed Codex work as current repository truth. Re-run a delta audit after Codex resumes and pushes.

## Executive summary

UseAgent has a coherent core design for a **file-first, provider-neutral multi-agent control plane**: repository-relative path validation, a scoped task ledger, one-active-writer conflict detection, explicit report/review lifecycle, bounded worker runners, durable checkpoints, and a CI matrix for Python 3.11–3.13. The remote HEAD inspected here had a successful GitHub Actions CI run.

The main architectural concern is that some guarantees currently read stronger than the technical boundary actually provides. UseAgent is a coordination protocol, not an OS/filesystem sandbox. In addition, raw subprocess output is persisted under a tracked evidence directory, the QA path executes project-controlled shell strings, and production readiness can consume QA state that is not cryptographically tied to the current repository snapshot.

**Snapshot assessment:** suitable for trusted/local experimental and open-source use after understanding the trust model; **not yet a strong security boundary for mutually untrusted agents or repositories**.

### Finding counts

| Severity | Count |
|---|---:|
| High | 3 |
| Medium | 3 |
| Low | 2 |
| Informational / strengths | 1 group |

## Scope reviewed

Repository-level audit covered:

- package/CLI architecture (`pyproject.toml`, `tools/useagent.py`)
- multi-agent task lifecycle and role boundaries
- path/scope validation and concurrency model
- automatic runner execution
- QA execution and evidence persistence
- production/readiness gate semantics
- configuration schema and validation
- unit-test strategy and GitHub Actions CI
- security policy and ignore rules
- tracked runtime/evidence layout
- public documentation claims and stated trust model

Primary snapshot anchors:

- `tools/useagent.py`: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/tools/useagent.py
- `tests/test_useagent.py`: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/tests/test_useagent.py
- `useagent.config.json`: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/useagent.config.json
- `AGENTS.md`: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/AGENTS.md
- `README.md`: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/README.md
- CI: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/.github/workflows/ci.yml
- security policy: https://github.com/thuanlyt/UseAgent/blob/0fd2244d68b8429213f0cbc6d7beaeb916f37620/SECURITY.md

## Positive controls already present

These are meaningful strengths and should be preserved while hardening:

1. **Repository boundary checks.** `safe_repo_path()` resolves configured paths and rejects paths escaping the project root; relative scope validation rejects absolute paths and `..` traversal.
2. **Single-writer coordination.** Active scopes are checked for prefix overlap before claim/dispatch, reducing accidental concurrent edits.
3. **Explicit lifecycle.** A worker cannot jump directly to `done`; reporting and review evidence are distinct states/actions.
4. **Role checks.** Worker/reviewer/release roles have separate lifecycle permissions in the CLI protocol.
5. **Report filtering.** Ingested report file paths are revalidated and out-of-scope/unsafe reported paths are ignored with warning evidence.
6. **Safer runner invocation.** Configured worker runners use argv arrays and `shell=False`, include a required assignment placeholder, and have bounded timeout/wait controls.
7. **Atomic state writes.** JSON/Markdown state uses temporary-file replacement, and critical registry/config transitions are serialized through a lock.
8. **Useful CI breadth.** CI compiles Python, runs unit tests, validates protocol structure, validates/builds docs, and smoke-tests the installed console package on Python 3.11/3.12/3.13.
9. **No third-party runtime dependency.** The package is intentionally dependency-free at runtime, reducing dependency attack surface.

## Findings

### UA-AUD-001 — HIGH — Raw runner/QA output can leak secrets into tracked evidence

**Where**

- `write_runner_evidence()` writes runner command, stdout and stderr to `work/evidence/...` (stdout/stderr are clipped but not redacted).
- `run_qa()` captures stdout/stderr and writes them to a QA evidence Markdown file without secret redaction; QA output is not bounded by the same clipping helper.
- `.gitignore` ignores `.env*` but does **not** ignore `work/evidence/`.
- The remote repository already tracks many files under `work/evidence/`, so persistence is not merely theoretical.

**Impact**

A child process/test/agent that prints an API token, OAuth credential, authorization header, cookie, environment variable, private URL, or other sensitive value can cause it to be stored in a repository file and later committed/pushed. Large QA output can also create unnecessary repository growth or local disk pressure.

**Recommended fix**

- Introduce one central `sanitize_evidence(text)` path used by runner and QA evidence.
- Redact common credential formats plus configurable secret values sourced from environment names, without writing the original values anywhere.
- Clip **both** stdout and stderr for QA and runner output, and record byte counts/hashes for truncated output.
- Prefer short structured evidence (`command`, exit code, duration, test counts, artifact path) over full logs.
- Treat raw logs as ephemeral/local by default; if they must exist, store them outside Git-tracked paths or explicitly `.gitignore` a raw-log subdirectory.
- Add regression tests proving representative token/auth/header values never reach persisted evidence.

### UA-AUD-002 — HIGH (trust-boundary dependent) — QA uses `shell=True` on repository-controlled strings

**Where**

`run_qa()` iterates `supervisor.qa_commands` and calls `subprocess.run(str(command), shell=True, ...)`. The default config is benign, but UseAgent also supports operating on other prepared repositories via `--root`.

**Impact**

Running `supervisor qa` or a QA-enabled cycle on a repository/config that has not been trusted can execute arbitrary shell syntax. Tests are inherently executable code, but `shell=True` broadens the command surface and makes shell metacharacters/expansion part of the contract even when a direct executable invocation would suffice.

**Recommended fix**

- Change the default QA schema to argv arrays and run with `shell=False`.
- If shell composition is needed, make it an explicit opt-in object such as `{ "shell": "...", "trusted": true }` and surface a clear warning/approval gate.
- Optionally hash the resolved QA configuration into evidence so the exact command set that produced a gate is auditable.
- Document clearly that a target repository's QA configuration is executable local code and must be reviewed before first run.

### UA-AUD-003 — HIGH — Production QA gate is not tied to the current source snapshot

**Where**

`production_snapshot()` evaluates `state["last_qa"]["status"]`. The state does not bind the QA result to the current Git commit/tree/content hash. `run_qa_each_cycle` is `false` in the default repository config.

**Impact**

A previously passing QA result can remain in supervisor state after source changes. A later production snapshot can therefore treat `qa` as passing without proving that the currently reviewed code is the code that passed QA. This weakens the semantic promise of a production/release gate.

**Recommended fix**

- Record `git HEAD`, dirty-tree status, and preferably a deterministic tree/content fingerprint in each QA evidence record.
- Production gate must require the current fingerprint to equal the QA fingerprint.
- Any relevant source/config change should invalidate cached QA state.
- If Git is unavailable, fall back to a hash of declared source/config paths and mark the gate `manual` rather than silently accepting stale QA.

### UA-AUD-004 — MEDIUM — Scope ownership is coordination policy, not filesystem enforcement

**Where**

The ledger validates claimed scopes, prevents overlapping active assignments, and checks file paths that workers *report*. It does not intercept actual filesystem writes performed by an external Codex/Claude/Antigravity process.

**Impact**

A buggy, compromised, or simply non-compliant worker can modify files outside its claimed scope and omit those files from its report. The ledger can remain internally valid while the working tree violates the intended ownership model.

**Recommended fix**

For higher-assurance workflows:

- run each writer in an isolated Git worktree/container/sandbox;
- record a baseline commit/tree when a task is claimed;
- at report/review, compute the actual diff and reject changes outside claimed scope;
- require supervisor-controlled merge/cherry-pick rather than allowing workers to merge directly;
- describe `scope` as a protocol guarantee unless filesystem/diff enforcement is enabled.

### UA-AUD-005 — MEDIUM — Lock has no stale-owner recovery after abnormal process termination

**Where**

`state_lock()` uses create-if-absent (`O_CREAT | O_EXCL`) on `work/.state.lock`, writes PID/time metadata, waits up to 30 seconds when present, and removes the lock in `finally`. There is no lease expiry or stale PID validation.

**Impact**

If the owning process is killed, the machine crashes, or Python exits without the `finally` cleanup, the lock can remain. Subsequent commands wait and then fail until a human removes it.

**Recommended fix**

- Prefer an OS-native advisory lock where practical, or use a lease with PID + process-start identity + timestamp.
- On contention, verify the recorded owner is alive and that the lease is not stale before reclaiming.
- Keep conservative behavior on ambiguous cases and provide a dedicated `doctor/lock-status` command rather than asking users to delete files blindly.
- Add crash/stale-lock regression tests.

### UA-AUD-006 — MEDIUM — Role identity is logical, not authenticated

**Where**

Review/claim authorization is based on an agent ID/role from local config and a CLI `--agent` argument. This correctly prevents accidental lifecycle misuse inside the protocol, but it is not an identity/authentication mechanism.

**Impact**

Any local process with write/execute access to the repository can potentially invoke commands while naming a registered reviewer/release agent. This is acceptable for a single trusted developer machine, but it should not be presented as a security boundary between mutually untrusted agents/users.

**Recommended fix**

- Explicitly document the trusted-local-process assumption.
- For team/remote runners, introduce signed report identity or externally authenticated runner identity (CI identity, service account, signed envelope) if stronger separation is needed.
- Keep role checks as workflow policy even if stronger identity is later added.

### UA-AUD-007 — LOW — QA timeout and evidence-size validation are asymmetric

Runner timeout is explicitly bounded (`1..86400`), while `qa_timeout_seconds` validation only requires a positive integer. QA output persistence is also less bounded than runner evidence.

**Recommended fix:** define maximum QA timeout, maximum output bytes per command, total evidence budget per cycle, and tests for those limits.

### UA-AUD-008 — LOW — CI supply-chain hardening can be stronger

CI permissions are appropriately narrow (`contents: read`), but actions are referenced by release tags such as `actions/checkout@v7.0.1` and `actions/setup-python@v7.0.0`, not immutable commit SHAs.

**Recommended fix:** for a high-assurance release profile, pin third-party actions to full commit SHAs and let Dependabot/Renovate propose upgrades.

## Production-gate semantics review

The configured `production_gates` strings are descriptive configuration; the implemented production snapshot evaluates a fixed set of machine checks (`all_tasks_done`, last QA state, no blocked tasks, readiness-file presence). Operational/readiness files are checked primarily for existence/non-empty content rather than semantic completeness.

Recommendation: either (a) rename/document these as advisory gate descriptions, or (b) evolve them into structured machine-checkable gates with explicit evidence predicates. Do not imply arbitrary free-text `production_gates` are currently enforced.

## Testing and CI assessment

The test suite is substantial and explicitly exercises lifecycle transitions, scope conflicts, agent capacity/availability, report authentication/filtering, unsafe paths, runner timeout/bounded wait, malformed config/registry handling, and review evidence requirements. This is a strong match to the core state machine.

Remote CI at the audited HEAD completed successfully and the workflow covers Python 3.11, 3.12 and 3.13 plus docs and package smoke tests.

Gaps worth adding as regression suites after the findings above are addressed:

- secret redaction in runner + QA evidence
- QA evidence snapshot/hash invalidation after source changes
- stale lock/crash recovery
- actual Git diff vs declared task scope
- malicious/shell-like QA configuration schema
- QA output-size and timeout upper bounds
- concurrent multi-process stress/fuzz tests on state transitions

## Architecture / maintainability notes

`tools/useagent.py` is a deliberately dependency-free single control-plane module and is currently large (roughly 90 KB), while the principal unit-test module is also large. This is not a defect by itself, but as runner adapters, policies, identity, and production gates grow, separating modules would reduce review blast radius.

A reasonable future split without changing behavior:

- `state.py`: atomic writes, lock, registry/config
- `scope.py`: normalization, overlap, path safety
- `lifecycle.py`: task/role transitions
- `runner.py`: runner execution + evidence
- `qa.py`: QA execution + snapshot binding
- `supervisor.py`: dispatch/cycle/gates
- `cli.py`: argparse only

Keep a small compatibility entry point at `tools/useagent.py` if the public CLI/path is already documented.

## Suggested remediation order

1. **P0 for next release:** fix evidence secret leakage and bind QA evidence to source snapshot.
2. **P0/P1 depending threat model:** replace default `shell=True` QA strings with argv-safe execution; explicitly mark shell mode trusted/opt-in.
3. Add stale-lock recovery.
4. Add Git-diff scope reconciliation / worktree isolation mode.
5. Clarify role/security boundary and production-gate semantics in docs.
6. Add timeout/output budgets and immutable CI action pins.
7. Refactor monolithic implementation only after behavior is protected by regression tests.

## Codex-in-progress reconciliation

The screenshot supplied with this audit indicates Codex stopped due to quota while working through a newer checkpoint. Because that working tree is not the remote snapshot, **do not ask Codex to blindly re-apply this report as patches**. When quota resets:

1. Let Codex inspect its own working tree and checkpoint first.
2. Push/commit its current coherent state (or a dedicated branch if that is the project's policy).
3. Diff that state against snapshot `0fd2244...`.
4. Re-check each finding in this report against the new code; close only findings demonstrably fixed by code + tests.
5. Run the full CI/QA gate on the new snapshot.
6. Generate a short `audit/DELTA_AUDIT_<date>.md` with resolved/open/new findings.

This avoids overwriting or duplicating the work that was already in flight when the Codex quota was exhausted.

## Final status

**Remote snapshot verdict: `CONDITIONAL PASS / HARDEN BEFORE STRONG-TRUST CLAIMS`.**

The core orchestration state machine is thoughtfully defended against accidental misuse and path/report corruption, and the current remote CI is green. The remaining high-priority work is mainly about **trust boundaries and evidence integrity**, especially raw log persistence, shell-based QA execution, and proving that a production QA pass belongs to the exact source snapshot being released.
