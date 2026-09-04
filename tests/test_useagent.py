from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tomllib

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

    def register_reviewer(self, agent_id: str = "reviewer", scope: str = ".") -> None:
        code, _, error = self.invoke("agent", "register", "--id", agent_id, "--role", "reviewer", "--scope", scope)
        self.assertEqual((code, error), (0, ""))

    def test_dependency_and_done_requirements(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_worker("worker-2", ".")
        self.register_reviewer()
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
        self.assertIn("not authorized for review actions", error)

        code, _, error = self.invoke("task", "evidence", first, "--kind", "test", "--value", "unit test: pass")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            first,
            "--agent",
            "worker-1",
            "--result",
            "completed",
            "--summary",
            "Implemented first task",
            "--next-action",
            "Review and QA",
            "--file",
            "src/first.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", first, "--status", "needs_review", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("not authorized for review actions", error)
        code, _, error = self.invoke(
            "task", "evidence", first, "--kind", "review", "--agent", "worker-1", "--value", "worker self-review"
        )
        self.assertEqual(code, 2)
        self.assertIn("not authorized for review actions", error)
        code, _, error = self.invoke(
            "task", "evidence", first, "--kind", "review", "--agent", "reviewer", "--value", "review pass"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", first, "--status", "needs_review", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", first, "--status", "done", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        item_text = (useagent.ROOT / "work" / "items" / f"{first}.md").read_text(encoding="utf-8")
        self.assertIn("status: done", item_text)
        code, _, error = self.invoke("task", "claim", second, "--agent", "worker-2")
        self.assertEqual((code, error), (0, ""))

    def test_overlapping_active_writer_is_rejected(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_worker("worker-2", ".")
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

    def test_task_scope_can_be_extended_through_update(self) -> None:
        self.register_worker("worker-1", ".")
        task_id = self.new_task("Extend owned paths", "src/api.py")
        code, _, error = self.invoke(
            "task",
            "claim",
            task_id,
            "--agent",
            "worker-1",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "update",
            task_id,
            "--status",
            "in_progress",
            "--agent",
            "worker-1",
            "--scope",
            "tests/test_api.py",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(
            registry["items"][task_id]["scope"],
            ["src/api.py", "tests/test_api.py"],
        )

    def test_scope_overlap_uses_boundaries_and_windows_case_rules(self) -> None:
        self.assertFalse(useagent.scope_overlaps("src/api.py", "src/web.py"))
        self.assertTrue(useagent.scope_overlaps("src", "src/web.py"))
        expected_case_match = os.path.normcase("src") == os.path.normcase("SRC")
        self.assertEqual(useagent.scope_overlaps("src", "SRC"), expected_case_match)

    def test_task_claim_requires_registered_agent(self) -> None:
        task_id = self.new_task("Registered worker only", "src/claim.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "unregistered")
        self.assertEqual(code, 2)
        self.assertIn("unknown registered agent", error)

        self.register_worker("worker-1", ".")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))

    def test_scope_traversal_and_out_of_scope_reports_are_rejected(self) -> None:
        code, _, error = self.invoke(
            "task",
            "new",
            "--title",
            "Reject traversal",
            "--level",
            "L1",
            "--owner",
            "worker",
            "--scope",
            "../outside",
            "--acceptance",
            "safe scope",
        )
        self.assertEqual(code, 2)
        self.assertIn("parent traversal", error)

        self.register_worker("worker-1", "src")
        task_id = self.new_task("Report only owned files", "src")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            task_id,
            "--agent",
            "worker-1",
            "--result",
            "completed",
            "--summary",
            "attempted report",
            "--next-action",
            "review",
            "--file",
            "tests/secret.py",
        )
        self.assertEqual(code, 2)
        self.assertIn("outside task scope", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")
        self.assertEqual(registry["items"][task_id]["reports"], [])

    def test_worker_pull_rejects_unsafe_assignment_without_state_change(self) -> None:
        self.register_worker("frontend", "src/frontend")
        task_id = self.new_task("Safe assignment path", "src/frontend/app.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        registry["items"][task_id]["assignment_path"] = "../outside.md"
        useagent.REGISTRY.write_text(json.dumps(registry), encoding="utf-8")

        code, _, error = self.invoke("worker", "pull", "--agent", "frontend")
        self.assertEqual(code, 2)
        self.assertIn("leaves project root", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "assigned")

    def test_done_requires_explicit_review_gate(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_reviewer()
        task_id = self.new_task("Review before done", "src/review.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "evidence", task_id, "--kind", "test", "--value", "pass")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("not authorized for review actions", error)
        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("not authorized for review actions", error)
        code, _, error = self.invoke(
            "task", "evidence", task_id, "--kind", "review", "--agent", "worker-1", "--value", "worker self-review"
        )
        self.assertEqual(code, 2)
        self.assertIn("not authorized for review actions", error)
        code, _, error = self.invoke(
            "task",
            "report",
            task_id,
            "--agent",
            "worker-1",
            "--result",
            "completed",
            "--summary",
            "Implementation complete",
            "--next-action",
            "Review",
            "--file",
            "src/review.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task", "evidence", task_id, "--kind", "review", "--agent", "reviewer", "--value", "review pass"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))

    def test_supervisor_ingest_authenticates_reports_and_filters_files(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Authenticate worker report", "src")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))

        reports_dir = useagent.ROOT / "work" / "reports" / "inbox"
        spoofed = reports_dir / "spoofed.md"
        spoofed.write_text(
            "---\n"
            "type: useagent-worker-report\n"
            f"task_id: {task_id}\n"
            "agent: attacker\n"
            "result: completed\n"
            "files: [\"src/owned.py\"]\n"
            "---\n\nspoofed\n",
            encoding="utf-8",
        )
        code, output, error = self.invoke("supervisor", "ingest")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "no new reports")
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")
        self.assertEqual(registry["items"][task_id]["reports"], [])
        spoofed.unlink()

        valid = reports_dir / "valid.md"
        valid.write_text(
            "---\n"
            "type: useagent-worker-report\n"
            f"task_id: {task_id}\n"
            "agent: worker-1\n"
            "result: completed\n"
            "files: [\"src/owned.py\", \"tests/secret.py\", \"../outside.py\"]\n"
            "---\n\nvalid\n",
            encoding="utf-8",
        )
        code, _, error = self.invoke("supervisor", "ingest")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["status"], "reported")
        self.assertEqual(item["files"], ["src/owned.py"])
        self.assertTrue(any(entry["kind"] == "warning" for entry in item["evidence"]))

    def test_supervisor_ingest_ignores_unreadable_reports_without_state_change(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Ignore unreadable report", "src")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        unreadable = useagent.ROOT / "work" / "reports" / "inbox" / "unreadable.md"
        unreadable.write_bytes(b"\xff\xfe\xfa")
        code, output, error = self.invoke("supervisor", "ingest")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "no new reports")
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")
        self.assertEqual(registry["items"][task_id]["reports"], [])

    def test_agent_list_skips_malformed_roster_entry_without_traceback(self) -> None:
        self.register_worker("worker-1", ".")
        config = useagent.load_config()
        config["agents"].insert(0, None)
        useagent.save_config(config)
        code, output, error = self.invoke("agent", "list")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("worker-1", output)
        self.assertNotIn("Traceback", output + error)

    def test_worker_pull_rejects_non_string_assignment_without_state_change(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Typed assignment path", "src/assignment.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        registry["items"][task_id]["assignment_path"] = ["invalid"]
        useagent.REGISTRY.write_text(json.dumps(registry), encoding="utf-8")

        code, _, error = self.invoke("worker", "pull", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("invalid assignment path", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "assigned")

    def test_worker_pull_rejects_unreadable_assignment_without_state_change(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Readable assignment", "src/readable.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        assignment = useagent.ROOT / registry["items"][task_id]["assignment_path"]
        assignment.write_bytes(b"\xff\xfe\xfa")

        code, _, error = self.invoke("worker", "pull", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("assignment file cannot be read", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "assigned")

    def test_validator_reports_malformed_config_without_traceback(self) -> None:
        config = useagent.load_config()
        config["supervisor"]["qa_timeout_seconds"] = 0
        config["agents"] = [
            {
                "role": "worker",
                "status": "available",
                "scope": [],
                "max_active": 0,
                "inbox": 123,
            }
        ]
        errors: list[str] = []
        useagent.validate_config(config, errors)
        self.assertTrue(any("qa_timeout_seconds" in error for error in errors))
        self.assertTrue(any("invalid or duplicate agent id" in error for error in errors))
        self.assertTrue(any("agent needs an id" in error for error in errors))

    def test_validator_reports_malformed_config_sections_without_traceback(self) -> None:
        useagent.CONFIG.write_text(
            json.dumps({"paths": None, "supervisor": [], "agents": []}),
            encoding="utf-8",
        )
        code, output, error = self.invoke("validate")
        self.assertEqual(code, 1)
        self.assertIn("config.paths must be an object", output)
        self.assertIn("config.supervisor must be an object", output)
        self.assertNotIn("Traceback", output + error)

    def test_validator_reports_malformed_registry_arrays_without_traceback(self) -> None:
        task_id = self.new_task("Registry array validation", "src/registry.py")
        data = useagent.load_registry()
        data["items"][task_id]["depends_on"] = None
        data["items"][task_id]["files"] = {"bad": "shape"}
        data["items"][task_id]["reports"] = "not-an-array"
        data["items"][task_id]["status"] = "done"
        data["items"][task_id]["evidence"] = 1
        errors: list[str] = []
        useagent.validate_registry(data, errors)
        self.assertIn(f"{task_id} depends_on must be an array", errors)
        self.assertIn(f"{task_id} files must be an array", errors)
        self.assertIn(f"{task_id} reports must be an array", errors)
        self.assertIn(f"{task_id} evidence must be an array", errors)

    def test_task_update_rejects_unsafe_or_out_of_scope_recorded_files(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Safe recorded file", "src/owned.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "update",
            task_id,
            "--status",
            "in_progress",
            "--agent",
            "worker-1",
            "--file",
            "../outside.py",
        )
        self.assertEqual(code, 2)
        self.assertIn("parent traversal", error)
        code, _, error = self.invoke(
            "task",
            "update",
            task_id,
            "--status",
            "in_progress",
            "--agent",
            "worker-1",
            "--file",
            "tests/secret.py",
        )
        self.assertEqual(code, 2)
        self.assertIn("outside task scope", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["files"], [])

    def test_done_registry_requires_review_evidence(self) -> None:
        task_id = self.new_task("Review evidence is required", "src/review-gate.py")
        data = useagent.load_registry()
        data["items"][task_id]["status"] = "done"
        data["items"][task_id]["evidence"] = [{"kind": "test", "value": "pass"}]
        errors: list[str] = []
        useagent.validate_registry(data, errors)
        self.assertIn(f"{task_id} is done without review evidence", errors)

    def test_update_cannot_bypass_claim(self) -> None:
        task_id = self.new_task("Claimed only through the CLI", "src/claim.py")
        code, _, error = self.invoke("task", "update", task_id, "--status", "in_progress", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("task claim", error)

    def test_reported_status_requires_worker_report(self) -> None:
        self.register_worker("worker-1", ".")
        task_id = self.new_task("Report-only completion", "src/report-only.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))

        code, _, error = self.invoke("task", "update", task_id, "--status", "reported", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("use task report for a worker completion", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")
        self.assertEqual(registry["items"][task_id]["reports"], [])

        code, _, error = self.invoke(
            "task",
            "report",
            task_id,
            "--agent",
            "worker-1",
            "--result",
            "completed",
            "--summary",
            "Implementation complete",
            "--next-action",
            "Review",
            "--file",
            "src/report-only.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "reported")
        self.assertEqual(len(registry["items"][task_id]["reports"]), 1)

    def test_dispatch_pull_report_and_supervisor_cycle(self) -> None:
        self.register_worker()
        self.register_reviewer()
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
        self.assertFalse((useagent.ROOT / "work" / "agents" / "frontend" / "REPORT.md").read_text(encoding="utf-8").endswith("\n\n"))

        code, _, error = self.invoke("supervisor", "cycle")
        self.assertEqual((code, error), (0, ""))
        supervisor_report = (useagent.ROOT / "work" / "SUPERVISOR_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("awaiting review", supervisor_report)
        self.assertIn("worker report", supervisor_report)

        code, _, error = self.invoke(
            "task", "evidence", task_id, "--kind", "review", "--agent", "reviewer", "--value", "review pass"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "reviewer")
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

    def test_explicit_root_switches_runtime_state(self) -> None:
        target_root = Path(self.temp_dir.name) / "selected-project"
        target_root.mkdir()

        code, _, error = self.invoke("--root", str(target_root), "init")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(useagent.ROOT, target_root.resolve())
        self.assertTrue((target_root / "work" / "registry.json").exists())
        self.assertTrue((target_root / "useagent.config.json").exists())

        code, task_id, error = self.invoke(
            "--root",
            str(target_root),
            "task",
            "new",
            "--title",
            "Target-root task",
            "--level",
            "L1",
            "--owner",
            "worker",
            "--scope",
            "src/app.py",
            "--acceptance",
            "target root is used",
        )
        self.assertEqual((code, error), (0, ""))
        task_id = task_id.strip()
        self.assertTrue((target_root / "work" / "items" / f"{task_id}.md").exists())
        self.assertFalse((Path(self.temp_dir.name) / "work" / "items" / f"{task_id}.md").exists())

    def test_explicit_root_rejects_paths_outside_selected_root(self) -> None:
        target_root = Path(self.temp_dir.name) / "selected-project"
        target_root.mkdir()
        code, _, error = self.invoke("--root", str(target_root), "init")
        self.assertEqual((code, error), (0, ""))

        with self.assertRaises(useagent.UseAgentError):
            useagent.safe_repo_path("../outside")

        missing_root = target_root / "does-not-exist"
        code, _, error = self.invoke("--root", str(missing_root), "validate")
        self.assertEqual(code, 2)
        self.assertIn("project root does not exist", error)

    def test_package_metadata_declares_supported_cli(self) -> None:
        metadata = tomllib.loads((self.original_root / "pyproject.toml").read_text(encoding="utf-8"))
        project = metadata["project"]
        self.assertEqual(project["name"], "useagent")
        self.assertEqual(project["license"], {"file": "LICENSE"})
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["scripts"]["useagent"], "tools.useagent:main")
        self.assertEqual(metadata["tool"]["setuptools"]["packages"], ["tools"])

    def test_supervisor_prioritizes_review_gate_before_new_work(self) -> None:
        config = useagent.load_config()
        data = {"items": {"UA-9000": {"id": "UA-9000", "title": "Review this change", "status": "needs_review"}}}
        action = useagent.choose_next_action(data, [], config, {"status": "pass"})
        self.assertIn("Complete the review gate for UA-9000", action)

        data["items"]["UA-9000"]["status"] = "reported"
        action = useagent.choose_next_action(data, [], config, {"status": "pass"})
        self.assertIn("Review worker report for UA-9000", action)

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

    def test_production_snapshot_checks_operational_readiness_files(self) -> None:
        (useagent.ROOT / "docs").mkdir(parents=True, exist_ok=True)
        (useagent.ROOT / "docs" / "operations.md").write_text("Operational runbook", encoding="utf-8")
        (useagent.ROOT / "docs" / "rollback.md").write_text("Rollback plan", encoding="utf-8")
        config = useagent.load_config()
        config["supervisor"]["operational_readiness_files"] = ["docs/operations.md", "docs/rollback.md"]
        data = useagent.load_registry()
        data["items"]["UA-9999"] = {"status": "done"}
        state = {"last_qa": {"status": "pass"}}
        gates, ready = useagent.production_snapshot(config, data, state)
        self.assertEqual(dict(gates)["operational_rollback_notes"], "pass")
        self.assertTrue(ready)

        config["supervisor"]["operational_readiness_files"] = ["docs/missing.md"]
        gates, ready = useagent.production_snapshot(config, data, state)
        self.assertEqual(dict(gates)["operational_rollback_notes"], "manual")
        self.assertFalse(ready)

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
        state = json.loads((useagent.ROOT / "work" / "supervisor" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["last_checkpoint"], output.strip())
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
