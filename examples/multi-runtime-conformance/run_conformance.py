#!/usr/bin/env python3
"""Run a credential-free conformance check across three runtime identities.

The identities model Codex, Claude Code and Google Antigravity sessions, but
the harness deliberately calls only the public UseAgent CLI. This proves the
shared-folder protocol and routing rules without pretending to test a vendor
API or launch an external model.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLI = REPOSITORY_ROOT / "tools" / "useagent.py"

RUNTIMES = (
    {
        "id": "codex-backend",
        "label": "Codex",
        "scope": "src/backend",
        "file": "src/backend/service.py",
        "capability": "python",
    },
    {
        "id": "claude-frontend",
        "label": "Claude Code",
        "scope": "src/frontend",
        "file": "src/frontend/app.ts",
        "capability": "web",
    },
    {
        "id": "antigravity-qa",
        "label": "Google Antigravity",
        "scope": "tests/qa",
        "file": "tests/qa/smoke.py",
        "capability": "browser",
    },
)


def run_cli(project_root: Path, *arguments: str) -> str:
    command = [sys.executable, str(CLI), "--root", str(project_root), *arguments]
    result = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def require(path: Path, label: str) -> None:
    if not path.exists():
        raise AssertionError(f"missing {label}: {path}")


def simulated_runner_args(runtime: dict[str, str]) -> list[str]:
    """Return an argv-only runner that reports through the real CLI."""

    runner_code = (
        "import pathlib, subprocess, sys\n"
        "cli = sys.argv[3]\n"
        "cmd = [sys.executable, cli, '--root', str(pathlib.Path.cwd()), 'task', 'report', sys.argv[1], '--agent', sys.argv[2], '--result', 'completed', '--summary', sys.argv[2] + ' automatic runner completed its isolated scope.', '--next-action', 'Supervisor ingest, review and QA.', '--file', sys.argv[4], '--check', 'automatic runner report: pass']\n"
        "raise SystemExit(subprocess.run(cmd, check=False).returncode)\n"
    )
    return [
        sys.executable,
        "-c",
        runner_code,
        "{task_id}",
        "{agent_id}",
        str(CLI),
        runtime["file"],
        "{assignment_path}",
    ]


def main() -> int:
    if not CLI.is_file():
        raise RuntimeError(f"cannot find UseAgent CLI: {CLI}")

    with tempfile.TemporaryDirectory(prefix="useagent-multi-runtime-") as temporary:
        project_root = Path(temporary)
        run_cli(project_root, "init")

        for runtime in RUNTIMES:
            source = project_root / runtime["file"]
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"# simulated {runtime['label']} scope\n", encoding="utf-8")

        config_path = project_root / "useagent.config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        quoted_python = json.dumps(sys.executable)
        config["supervisor"]["qa_commands"] = [
            f"{quoted_python} -c \"print('multi-runtime-qa-pass')\""
        ]
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

        task_ids: dict[str, str] = {}
        for runtime in RUNTIMES:
            register_args = [
                "agent",
                "register",
                "--id",
                runtime["id"],
                "--role",
                "worker",
                "--scope",
                runtime["scope"],
                "--capability",
                runtime["capability"],
                "--max-active",
                "1",
            ]
            for runner_arg in simulated_runner_args(runtime):
                register_args.append(f"--runner-arg={runner_arg}")
            run_cli(project_root, *register_args)
            task_ids[runtime["id"]] = run_cli(
                project_root,
                "task",
                "new",
                "--title",
                f"{runtime['label']} conformance task",
                "--objective",
                f"Exercise the shared protocol for the {runtime['label']} runtime identity.",
                "--level",
                "L1",
                "--owner",
                "supervisor",
                "--scope",
                runtime["file"],
                "--capability",
                runtime["capability"],
                "--acceptance",
                "assignment is routed to the matching runtime identity",
                "--acceptance",
                "worker pull and report are accepted through the public CLI",
                "--verification",
                "run the multi-runtime conformance harness",
            )

        dispatched = run_cli(project_root, "supervisor", "dispatch")
        registry = json.loads((project_root / "work" / "registry.json").read_text(encoding="utf-8"))
        for runtime in RUNTIMES:
            task_id = task_ids[runtime["id"]]
            item = registry["items"][task_id]
            if item["status"] != "assigned" or item["assigned_to"] != runtime["id"]:
                raise AssertionError(
                    f"{runtime['label']} was not routed correctly: "
                    f"status={item['status']} assigned_to={item.get('assigned_to')}"
                )
            if task_id not in dispatched:
                raise AssertionError(f"dispatch output omitted {task_id}")
            require(project_root / item["assignment_path"], f"{runtime['label']} assignment")

        for runtime in RUNTIMES:
            task_id = task_ids[runtime["id"]]
            run_output = run_cli(project_root, "worker", "run", "--agent", runtime["id"])
            if f"{task_id} runner_status=reported result=completed" not in run_output:
                raise AssertionError(f"{runtime['label']} runner did not complete {task_id}: {run_output}")

        cycle_output = run_cli(project_root, "supervisor", "cycle", "--run-qa")
        registry = json.loads((project_root / "work" / "registry.json").read_text(encoding="utf-8"))
        state = json.loads((project_root / "work" / "supervisor" / "state.json").read_text(encoding="utf-8"))
        for runtime in RUNTIMES:
            task_id = task_ids[runtime["id"]]
            item = registry["items"][task_id]
            if item["status"] != "reported":
                raise AssertionError(f"expected {task_id} to be reported, got {item['status']}")
            if item.get("files") != [runtime["file"]]:
                raise AssertionError(f"unexpected files for {task_id}: {item.get('files')}")
            require(project_root / f"work/agents/{runtime['id']}/REPORT.md", f"{runtime['label']} report log")
            require(project_root / f"work/agents/{runtime['id']}/COMPLETED.md", f"{runtime['label']} completed log")

        if state.get("last_qa", {}).get("status") != "pass":
            raise AssertionError(f"expected multi-runtime QA pass, got {state.get('last_qa')}")
        checkpoint = state.get("last_checkpoint")
        if not checkpoint:
            raise AssertionError("supervisor did not persist a checkpoint")
        require(project_root / checkpoint, "multi-runtime checkpoint")
        if "next=" not in cycle_output:
            raise AssertionError("supervisor cycle did not expose its next action")

        print("PASS: Codex + Claude Code + Antigravity identities assignment -> automatic runner -> report -> ingest -> QA -> checkpoint")
        print(f"tasks={','.join(task_ids.values())}")
        print(f"checkpoint={checkpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
