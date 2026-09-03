from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tools.useagent as useagent


class UseAgentCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_root = useagent.ROOT
        self.original_registry = useagent.REGISTRY
        self.original_config = useagent.CONFIG
        self.original_lock = useagent.LOCK
        useagent.ROOT = Path(self.temp_dir.name)
        useagent.REGISTRY = useagent.ROOT / "work" / "registry.json"
        useagent.CONFIG = useagent.ROOT / "useagent.config.json"
        useagent.LOCK = useagent.ROOT / "work" / ".state.lock"
        useagent.ensure_layout()
        (useagent.ROOT / "knowledge" / "INDEX.md").write_text("# UseAgent context index\ncompact", encoding="utf-8")
        (useagent.ROOT / "knowledge" / "project-map.md").write_text("# project map\nsmall", encoding="utf-8")

    def tearDown(self) -> None:
        useagent.ROOT = self.original_root
        useagent.REGISTRY = self.original_registry
        useagent.CONFIG = self.original_config
        useagent.LOCK = self.original_lock
        self.temp_dir.cleanup()

    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = useagent.main(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def new_task(self, title: str, scope: str, *dependencies: str) -> str:
        arguments = [
            "task",
            "new",
            "--title",
            title,
            "--level",
            "L1",
            "--owner",
            "worker",
            "--scope",
            scope,
            "--acceptance",
            "behavior passes",
        ]
        if dependencies:
            arguments.extend(["--depends-on", *dependencies])
        code, output, error = self.invoke(*arguments)
        self.assertEqual((code, error), (0, ""))
        return output.strip()

    def register_worker(self, agent_id: str = "frontend", scope: str = "src/frontend") -> None:
        code, _, error = self.invoke("agent", "register", "--id", agent_id, "--role", "worker", "--scope", scope)
        self.assertEqual((code, error), (0, ""))

    def test_dependency_and_done_requirements(self) -> None:
        first = self.new_task("First", "src/first.py")
        second = self.new_task("Second", "src/second.py", first)

        code, _, error = self.invoke("task", "claim", second, "--agent", "worker-2")
        self.assertEqual(code, 2)
        self.assertIn("unfinished dependencies", error)

        code, _, error = self.invoke("task", "claim", first, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        item_text = (useagent.ROOT / "work" / "items" / f"{first}.md").read_text(encoding="utf-8")
        self.assertIn("status: in_progress", item_text)
        self.assertIn("assigned_to: worker-1", item_text)
        code, _, error = self.invoke("task", "update", first, "--status", "done", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("evidence", error)

        code, _, error = self.invoke("task", "evidence", first, "--kind", "test", "--value", "unit test: pass")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", first, "--status", "done", "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        item_text = (useagent.ROOT / "work" / "items" / f"{first}.md").read_text(encoding="utf-8")
        self.assertIn("status: done", item_text)
        code, _, error = self.invoke("task", "claim", second, "--agent", "worker-2")
        self.assertEqual((code, error), (0, ""))

    def test_overlapping_active_writer_is_rejected(self) -> None:
        first = self.new_task("Parent scope", "src")
        second = self.new_task("Nested scope", "src/feature.py")
        code, _, error = self.invoke("task", "claim", first, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "claim", second, "--agent", "worker-2")
        self.assertEqual(code, 2)
        self.assertIn("scope conflicts", error)

    def test_repeated_task_scopes_are_preserved(self) -> None:
        code, output, error = self.invoke(
            "task",
            "new",
            "--title",
            "Multiple owned paths",
            "--level",
            "L2",
            "--owner",
            "worker",
            "--scope",
            "src/api.py",
            "--scope",
            "tests/test_api.py",
            "--acceptance",
            "both paths are covered",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(
            registry["items"][output.strip()]["scope"],
            ["src/api.py", "tests/test_api.py"],
        )

    def test_update_cannot_bypass_claim(self) -> None:
        task_id = self.new_task("Claimed only through the CLI", "src/claim.py")
        code, _, error = self.invoke("task", "update", task_id, "--status", "in_progress", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("task claim", error)

    def test_dispatch_pull_report_and_supervisor_cycle(self) -> None:
        self.register_worker()
        task_id = self.new_task("Build frontend", "src/frontend/app.py")
        code, output, error = self.invoke("supervisor", "cycle")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("next=Workers pull", output)

        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["status"], "assigned")
        self.assertEqual(item["assigned_to"], "frontend")
        assignment = useagent.ROOT / item["assignment_path"]
        self.assertTrue(assignment.exists())
        self.assertTrue((useagent.ROOT / "work" / "outbox" / f"{task_id}-to-frontend.md").exists())
        self.assertIn(task_id, (useagent.ROOT / "work" / "agents" / "frontend" / "INBOX.md").read_text(encoding="utf-8"))

        code, assignment_output, error = self.invoke("worker", "pull", "--agent", "frontend")
        self.assertEqual((code, error), (0, ""))
        self.assertIn(f"Assignment {task_id}", assignment_output)
        code, _, error = self.invoke(
            "task",
            "report",
            task_id,
            "--agent",
            "frontend",
            "--result",
            "completed",
            "--summary",
            "Implemented the feature",
            "--next-action",
            "Review and QA",
            "--file",
            "src/frontend/app.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "reported")
        self.assertIn(task_id, (useagent.ROOT / "work" / "completed" / "COMPLETED.md").read_text(encoding="utf-8"))
        self.assertIn(task_id, (useagent.ROOT / "work" / "agents" / "frontend" / "REPORT.md").read_text(encoding="utf-8"))

        code, _, error = self.invoke("supervisor", "cycle")
        self.assertEqual((code, error), (0, ""))
        supervisor_report = (useagent.ROOT / "work" / "SUPERVISOR_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("awaiting review", supervisor_report)
        self.assertIn("worker report", supervisor_report)

        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "frontend")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "frontend")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("supervisor", "report")
        self.assertEqual((code, error), (0, ""))
        supervisor_report = (useagent.ROOT / "work" / "SUPERVISOR_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("Completed tasks", supervisor_report)

    def test_worker_can_use_explicit_markdown_paths(self) -> None:
        code, _, error = self.invoke(
            "agent",
            "register",
            "--id",
            "qaagent",
            "--directory",
            "work/custom/qaagent",
            "--inbox-file",
            "work/mail/qa-inbox.md",
            "--report-file",
            "work/mail/qa-report.md",
            "--completed-file",
            "work/mail/qa-completed.md",
        )
        self.assertEqual((code, error), (0, ""))
        for path in ("work/mail/qa-inbox.md", "work/mail/qa-report.md", "work/mail/qa-completed.md"):
            self.assertTrue((useagent.ROOT / path).exists())

    def test_qa_command_is_captured_as_evidence(self) -> None:
        config = useagent.load_config()
        config["supervisor"]["qa_commands"] = ['python -c "print(\'qa-ok\')"']
        useagent.save_config(config)
        code, output, error = self.invoke("supervisor", "qa")
        self.assertEqual((code, error), (0, ""))
        self.assertIn('"status": "pass"', output)
        state = json.loads((useagent.ROOT / "work" / "supervisor" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["last_qa"]["status"], "pass")
        self.assertTrue((useagent.ROOT / state["last_qa"]["evidence"]).exists())

        config["supervisor"]["qa_commands"] = ['python -c "raise SystemExit(1)"']
        useagent.save_config(config)
        code, output, error = self.invoke("supervisor", "cycle", "--run-qa")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("create a scoped debug task", output)

    def test_bounded_context_and_checkpoint(self) -> None:
        task_id = self.new_task("Context task", "docs/context.md")
        code, output, error = self.invoke(
            "checkpoint",
            "create",
            "--name",
            "cycle one",
            "--status",
            "active",
            "--summary",
            "Created the first task",
            "--next-action",
            "Claim the task",
            "--task",
            task_id,
        )
        self.assertEqual((code, error), (0, ""))
        self.assertTrue((useagent.ROOT / output.strip()).exists())
        code, output, error = self.invoke("context", "--task", task_id, "--max-chars", "3000")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("knowledge/INDEX.md", output)
        self.assertIn(task_id, output)
        self.assertLessEqual(len(output), 3000)

    def test_project_validator_accepts_real_layout(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/useagent.py", "validate"],
            cwd=self.original_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "VALID")

    def test_context_command_runs_in_a_windows_console(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/useagent.py", "context", "--max-chars", "1200"],
            cwd=self.original_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UseAgent context index", result.stdout)


if __name__ == "__main__":
    unittest.main()
