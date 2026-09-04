#!/usr/bin/env python3
"""Run a credential-free UseAgent assignment/report conformance cycle.

The demo uses a temporary project root and the real CLI. The simulated worker
is still a normal UseAgent worker: it pulls an assignment and submits a report
through the public commands. No registry or task Markdown is edited directly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLI = REPOSITORY_ROOT / "tools" / "useagent.py"


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


def main() -> int:
    if not CLI.exists():
        raise RuntimeError(f"cannot find UseAgent CLI: {CLI}")

    with tempfile.TemporaryDirectory(prefix="useagent-conformance-") as temporary:
        project_root = Path(temporary)
        run_cli(project_root, "init")

        source_file = project_root / "src" / "demo.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("# simulated worker scope\n", encoding="utf-8")

        config_path = project_root / "useagent.config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        quoted_python = json.dumps(sys.executable)
        config["supervisor"]["qa_commands"] = [f"{quoted_python} -c \"print('demo-qa-pass')\""]
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

        run_cli(
            project_root,
            "agent",
            "register",
            "--id",
            "demo-worker",
            "--role",
            "worker",
            "--scope",
            "src",
            "--capability",
            "demo",
        )
        task_id = run_cli(
            project_root,
            "task",
            "new",
            "--title",
            "Conformance demo task",
            "--objective",
            "Prove the file-first worker handover protocol end to end.",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/demo.py",
            "--acceptance",
            "assignment is written to the worker mailbox",
            "--acceptance",
            "worker report is ingested by the supervisor",
            "--verification",
            "run this script from a clean checkout",
        )

        first_cycle = run_cli(project_root, "supervisor", "cycle")
        assignment_path = project_root / "work" / "agents" / "demo-worker" / "inbox" / f"{task_id}.md"
        outbox_path = project_root / "work" / "outbox" / f"{task_id}-to-demo-worker.md"
        inbox_index = project_root / "work" / "agents" / "demo-worker" / "INBOX.md"
        require(assignment_path, "worker assignment")
        require(outbox_path, "outbox prompt")
        require(inbox_index, "worker inbox index")
        if task_id not in inbox_index.read_text(encoding="utf-8"):
            raise AssertionError("dispatch did not expose the task id")
        if "cycle=" not in first_cycle:
            raise AssertionError("supervisor did not create a cycle")

        pulled = run_cli(project_root, "worker", "pull", "--agent", "demo-worker")
        if f"Assignment {task_id}" not in pulled:
            raise AssertionError("worker pull did not return the assignment")

        report_path = run_cli(
            project_root,
            "task",
            "report",
            task_id,
            "--agent",
            "demo-worker",
            "--result",
            "completed",
            "--summary",
            "Simulated worker completed the assigned scope.",
            "--next-action",
            "Supervisor ingest, review and QA.",
            "--file",
            "src/demo.py",
            "--check",
            "conformance worker check: pass",
        )

        second_cycle = run_cli(project_root, "supervisor", "cycle", "--run-qa")
        registry = json.loads((project_root / "work" / "registry.json").read_text(encoding="utf-8"))
        state = json.loads((project_root / "work" / "supervisor" / "state.json").read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        if item["status"] != "reported":
            raise AssertionError(f"expected reported task after ingest, got {item['status']}")
        if state["last_qa"]["status"] != "pass":
            raise AssertionError(f"expected QA pass, got {state['last_qa']}")
        if not state.get("last_checkpoint"):
            raise AssertionError("supervisor did not persist a checkpoint")

        require(project_root / report_path, "incoming worker report")
        require(project_root / "work" / "agents" / "demo-worker" / "REPORT.md", "worker report log")
        require(project_root / "work" / "agents" / "demo-worker" / "COMPLETED.md", "worker completed log")
        require(project_root / "work" / "completed" / "COMPLETED.md", "global completed log")
        require(project_root / "work" / "reports" / "REPORTS.md", "global report index")
        require(project_root / "work" / "SUPERVISOR_REPORT.md", "supervisor report")
        require(project_root / state["last_checkpoint"], "supervisor checkpoint")
        if "QA" not in second_cycle or "next=" not in second_cycle:
            raise AssertionError("supervisor cycle did not report QA and next action")

        print(f"PASS: {task_id} assignment -> pull -> report -> ingest -> QA -> checkpoint")
        print(f"report={report_path}")
        print(f"checkpoint={state['last_checkpoint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
