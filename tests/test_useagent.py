from __future__ import annotations

import contextlib
import copy
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

    def test_takeover_lineage_preserves_failure_and_scope(self) -> None:
        self.register_worker("blocked-worker", "src")
        predecessor = self.new_task("Preserve the failed task", "src/old.py")
        code, _, error = self.invoke("task", "claim", predecessor, "--agent", "blocked-worker")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            predecessor,
            "--agent",
            "blocked-worker",
            "--result",
            "blocked",
            "--summary",
            "The first attempt hit a preserved blocker",
            "--next-action",
            "Create a bounded takeover after review",
            "--file",
            "src/old.py",
            "--check",
            "blocker recorded",
        )
        self.assertEqual((code, error), (0, ""))

        code, output, error = self.invoke(
            "task",
            "new",
            "--title",
            "Take over the failed task",
            "--level",
            "L2",
            "--owner",
            "supervisor",
            "--scope",
            "src/recovery.py",
            "--scope",
            "tests/recovery.py",
            "--acceptance",
            "recovery behavior passes",
            "--supersedes",
            predecessor,
            "--takeover-reason",
            "Quota fallback after preserved failure",
        )
        self.assertEqual((code, error), (0, ""))
        successor = output.strip()
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        predecessor_item = registry["items"][predecessor]
        successor_item = registry["items"][successor]
        self.assertEqual(predecessor_item["status"], "blocked")
        self.assertEqual(predecessor_item["superseded_by"], successor)
        self.assertEqual(successor_item["supersedes"], predecessor)
        self.assertEqual(successor_item["takeover_reason"], "Quota fallback after preserved failure")
        self.assertEqual(successor_item["scope"], ["src/recovery.py", "tests/recovery.py"])
        self.assertIsNone(successor_item["superseded_by"])
        predecessor_text = (useagent.ROOT / "work" / "items" / f"{predecessor}.md").read_text(encoding="utf-8")
        successor_text = (useagent.ROOT / "work" / "items" / f"{successor}.md").read_text(encoding="utf-8")
        self.assertIn(f"superseded_by: \"{successor}\"", predecessor_text)
        self.assertIn(f"supersedes: \"{predecessor}\"", successor_text)
        self.assertIn('takeover_reason: "Quota fallback after preserved failure"', successor_text)
        self.assertIn(f"superseded by {successor}: Quota fallback after preserved failure", predecessor_text)

        code, _, error = self.invoke("task", "claim", predecessor, "--agent", "blocked-worker")
        self.assertEqual(code, 2)
        self.assertIn(f"was superseded by {successor}", error)
        code, _, error = self.invoke("task", "update", predecessor, "--status", "planned", "--agent", "supervisor")
        self.assertEqual(code, 2)
        self.assertIn(f"was superseded by {successor}", error)
        unchanged = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))["items"][predecessor]
        self.assertEqual(unchanged["status"], "blocked")
        self.assertEqual(unchanged["superseded_by"], successor)

    def test_takeover_lineage_rejects_unsafe_predecessors_atomically(self) -> None:
        self.register_worker("lineage-worker", ".")
        active = self.new_task("Active predecessor", "src/active.py")
        code, _, error = self.invoke("task", "claim", active, "--agent", "lineage-worker")
        self.assertEqual((code, error), (0, ""))
        before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke(
            "task",
            "new",
            "--title",
            "Must reject active takeover",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/active-recovery.py",
            "--acceptance",
            "active safety passes",
            "--supersedes",
            active,
            "--takeover-reason",
            "Do not fork active work",
        )
        self.assertEqual(code, 2)
        self.assertIn("only blocked or cancelled", error)
        after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(after["items"], before["items"])

        self.register_worker("done-worker", ".")
        self.register_reviewer("lineage-reviewer")
        done = self.new_task("Done predecessor", "src/done.py")
        code, _, error = self.invoke("task", "claim", done, "--agent", "done-worker")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            done,
            "--agent",
            "done-worker",
            "--result",
            "completed",
            "--summary",
            "Done predecessor implementation",
            "--next-action",
            "Review",
            "--file",
            "src/done.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", done, "--status", "needs_review", "--agent", "lineage-reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "evidence",
            done,
            "--kind",
            "review",
            "--agent",
            "lineage-reviewer",
            "--value",
            "Done predecessor reviewed",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", done, "--status", "done", "--agent", "lineage-reviewer")
        self.assertEqual((code, error), (0, ""))
        before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke(
            "task",
            "new",
            "--title",
            "Must reject done takeover",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/done-recovery.py",
            "--acceptance",
            "done safety passes",
            "--supersedes",
            done,
            "--takeover-reason",
            "Do not reopen done work",
        )
        self.assertEqual(code, 2)
        self.assertIn("only blocked or cancelled", error)
        after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(after["items"], before["items"])

        before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke(
            "task",
            "new",
            "--title",
            "Must reject missing predecessor",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/missing-recovery.py",
            "--acceptance",
            "missing safety passes",
            "--supersedes",
            "UA-9999",
            "--takeover-reason",
            "No unknown predecessor",
        )
        self.assertEqual(code, 2)
        self.assertIn("unknown superseded task", error)
        after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(after["items"], before["items"])

        blocked = self.new_task("Missing reason predecessor", "src/missing-reason.py")
        data = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        data["items"][blocked]["status"] = "blocked"
        useagent.save_registry(data)
        before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke(
            "task",
            "new",
            "--title",
            "Must reject missing reason",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/missing-reason-recovery.py",
            "--acceptance",
            "reason safety passes",
            "--supersedes",
            blocked,
        )
        self.assertEqual(code, 2)
        self.assertIn("--takeover-reason must be non-empty", error)
        after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(after["items"], before["items"])

    def test_takeover_lineage_validator_and_legacy_compatibility(self) -> None:
        legacy = self.new_task("Legacy task", "src/legacy.py")
        data = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        for field in ("supersedes", "superseded_by", "takeover_reason"):
            data["items"][legacy].pop(field, None)
        legacy_errors: list[str] = []
        useagent.validate_registry(data, legacy_errors)
        self.assertFalse([error for error in legacy_errors if "supersed" in error or "takeover" in error])

        data["items"][legacy]["takeover_reason"] = "orphan reason"
        malformed_reason_errors: list[str] = []
        useagent.validate_registry(data, malformed_reason_errors)
        self.assertIn(f"{legacy} takeover_reason requires supersedes", malformed_reason_errors)

        predecessor = self.new_task("Validator predecessor", "src/predecessor.py")
        data = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        data["items"][predecessor]["status"] = "blocked"
        useagent.save_registry(data)
        code, output, error = self.invoke(
            "task",
            "new",
            "--title",
            "Validator successor",
            "--level",
            "L1",
            "--owner",
            "supervisor",
            "--scope",
            "src/successor.py",
            "--acceptance",
            "lineage validates",
            "--supersedes",
            predecessor,
            "--takeover-reason",
            "Recovery lineage is explicit",
        )
        self.assertEqual((code, error), (0, ""))
        successor = output.strip()
        valid = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        valid_errors: list[str] = []
        useagent.validate_registry(valid, valid_errors)
        self.assertFalse([error for error in valid_errors if "supersed" in error or "takeover" in error])

        broken = copy.deepcopy(valid)
        broken["items"][successor]["supersedes"] = "UA-9999"
        errors: list[str] = []
        useagent.validate_registry(broken, errors)
        self.assertIn(f"{successor} references missing superseded task UA-9999", errors)

        broken = copy.deepcopy(valid)
        broken["items"][predecessor]["superseded_by"] = None
        errors = []
        useagent.validate_registry(broken, errors)
        self.assertIn(f"{successor} supersedes {predecessor} without reciprocal superseded_by", errors)

        broken = copy.deepcopy(valid)
        broken["items"][successor]["takeover_reason"] = "line one\nline two"
        errors = []
        useagent.validate_registry(broken, errors)
        self.assertIn(f"{successor} takeover_reason must be a single line", errors)

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

    def test_task_claim_requires_available_agent_and_capacity(self) -> None:
        self.register_worker("worker-1", ".")
        task_id = self.new_task("Claim availability", "src/claim-availability.py")

        for status in ("paused", "offline", "busy"):
            code, _, error = self.invoke("agent", "status", "worker-1", "--status", status)
            self.assertEqual((code, error), (0, ""))
            registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
            code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
            self.assertEqual(code, 2)
            self.assertIn("expected available", error)
            registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
            self.assertEqual(registry_after["items"][task_id], registry_before["items"][task_id])

        code, _, error = self.invoke("agent", "status", "worker-1", "--status", "available")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))

        capacity_id = self.new_task("Claim capacity", "src/claim-capacity.py")
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke("task", "claim", capacity_id, "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("max_active capacity", error)
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][capacity_id], registry_before["items"][capacity_id])

    def test_worker_pull_requires_available_agent(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Pull availability", "src/pull-availability.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, _, error = self.invoke("agent", "status", "worker-1", "--status", "paused")
        self.assertEqual((code, error), (0, ""))
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        code, _, error = self.invoke("worker", "pull", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("expected available", error)
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][task_id], registry_before["items"][task_id])

        code, _, error = self.invoke("agent", "status", "worker-1", "--status", "available")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("worker", "pull", "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")

    def test_task_claim_rejects_scope_and_capability_mismatch(self) -> None:
        self.register_worker("scoped-worker", "src/allowed")
        outside_id = self.new_task("Claim scope mismatch", "src/other/task.py")
        code, _, error = self.invoke("task", "claim", outside_id, "--agent", "scoped-worker")
        self.assertEqual(code, 2)
        self.assertIn("outside the agent scope", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][outside_id]["status"], "planned")

        self.register_worker("capability-worker", ".")
        code, output, error = self.invoke(
            "task",
            "new",
            "--title",
            "Claim capability mismatch",
            "--level",
            "L1",
            "--owner",
            "worker",
            "--scope",
            "src/capability.py",
            "--capability",
            "browser-qa",
            "--acceptance",
            "capability is present",
        )
        self.assertEqual((code, error), (0, ""))
        capability_id = output.strip()
        code, _, error = self.invoke("task", "claim", capability_id, "--agent", "capability-worker")
        self.assertEqual(code, 2)
        self.assertIn("lacks required capabilities", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][capability_id]["status"], "planned")

    def test_agent_role_boundaries_are_enforced(self) -> None:
        self.register_reviewer()
        task_id = self.new_task("Review role cannot claim", "src/role-boundary.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "reviewer")
        self.assertEqual(code, 2)
        self.assertIn("not authorized to claim work", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "planned")

        code, _, error = self.invoke("agent", "register", "--id", "unknown-role", "--role", "rogue", "--scope", ".")
        self.assertEqual(code, 2)
        self.assertIn("invalid agent role", error)

        config = useagent.load_config()
        config["agents"][0]["role"] = "rogue"
        useagent.save_config(config)
        code, output, error = self.invoke("validate")
        self.assertEqual(code, 1)
        self.assertIn("invalid role for agent reviewer", output)

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
        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "reviewer")
        self.assertEqual(code, 2)
        self.assertIn("non-empty review evidence", error)
        code, _, error = self.invoke(
            "task", "evidence", task_id, "--kind", "review", "--agent", "reviewer", "--value", "review pass"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "done", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        for status in ("planned", "blocked", "cancelled"):
            code, _, error = self.invoke("task", "update", task_id, "--status", status, "--agent", "worker-1")
            self.assertEqual(code, 2)
            self.assertIn("tasks are terminal", error)
            registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
            self.assertEqual(registry["items"][task_id], registry_before["items"][task_id])

        cancelled_id = self.new_task("Terminal cancellation", "src/cancelled.py")
        code, _, error = self.invoke("task", "update", cancelled_id, "--status", "cancelled", "--agent", "reviewer")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", cancelled_id, "--status", "planned", "--agent", "reviewer")
        self.assertEqual(code, 2)
        self.assertIn("tasks are terminal", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][cancelled_id]["status"], "cancelled")

    def test_empty_review_evidence_is_rejected(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_reviewer()
        task_id = self.new_task("Reject empty review", "src/empty-review.py")
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
            "Implementation complete",
            "--next-action",
            "Review",
            "--file",
            "src/empty-review.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task", "evidence", task_id, "--kind", "review", "--agent", "reviewer", "--value", "   "
        )
        self.assertEqual(code, 2)
        self.assertIn("evidence kind and value cannot be empty", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "reported")
        self.assertEqual(
            [entry for entry in registry["items"][task_id]["evidence"] if entry.get("kind") == "review"], []
        )

    def test_review_requires_worker_report(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_reviewer()
        task_id = self.new_task("Report before review", "src/report-before-review.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "evidence", task_id, "--kind", "test", "--value", "unit test: pass")
        self.assertEqual((code, error), (0, ""))

        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "reviewer")
        self.assertEqual(code, 2)
        self.assertIn("a task must be reported before review", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")
        self.assertEqual(
            [entry for entry in registry["items"][task_id]["evidence"] if entry.get("kind") == "review"], []
        )

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
            "src/report-before-review.py",
            "--check",
            "unit test: pass",
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke("task", "update", task_id, "--status", "needs_review", "--agent", "reviewer")
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
        legacy_report = next(entry for entry in item["evidence"] if entry["kind"] == "worker-report")
        self.assertEqual(legacy_report["provenance"], "legacy")
        self.assertEqual(legacy_report["source"], "work/reports/inbox/valid.md")

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

    def reporting_runner(self, exit_code: int = 0) -> list[str]:
        runner_code = (
            "import pathlib, subprocess, sys\n"
            "if int(sys.argv[6]): raise SystemExit(int(sys.argv[6]))\n"
            "cli = sys.argv[3]\n"
            "cmd = [sys.executable, cli, '--root', str(pathlib.Path.cwd()), 'task', 'report', sys.argv[1], '--agent', sys.argv[2], '--result', 'completed', '--summary', 'automatic runner report', '--next-action', 'review', '--file', sys.argv[4], '--check', 'automatic runner report: pass']\n"
            "raise SystemExit(subprocess.run(cmd, check=False).returncode)\n"
        )
        return [
            sys.executable,
            "-c",
            runner_code,
            "{task_id}",
            "{agent_id}",
            str(Path(useagent.__file__).resolve()),
            "src/runner.py",
            "{assignment_path}",
            str(exit_code),
        ]

    def configure_runner(self, command: list[str], timeout_seconds: int = 30) -> None:
        config = useagent.load_config()
        config["agents"][0]["runner"] = {
            "command": command,
            "timeout_seconds": timeout_seconds,
        }
        useagent.save_config(config)

    def configure_qa(self, command: str = 'python -c "print(\'qa-pass\')"') -> dict:
        config = useagent.load_config()
        config["supervisor"]["qa_commands"] = [command]
        useagent.save_config(config)
        return config

    def successful_qa(self, command: str = 'python -c "print(\'qa-pass\')"') -> tuple[dict, dict]:
        config = self.configure_qa(command)
        result = useagent.run_qa(config, "source-state-test")
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["source_fingerprint"])
        return config, result

    def release_data_with_done_task(self) -> dict:
        data = useagent.load_registry()
        data["items"]["UA-9999"] = {"status": "done"}
        return data

    def initialize_git_baseline(self) -> None:
        commands = [
            ["git", "init", "-q"],
            ["git", "config", "user.email", "useagent-tests@example.test"],
            ["git", "config", "user.name", "UseAgent Tests"],
            ["git", "add", "-A"],
            ["git", "commit", "-qm", "test baseline"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=useagent.ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)

    def git_output(self, *arguments: str, input_text: str | None = None) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=useagent.ROOT,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def configure_tracking_ref(self, branch: str, commit: str) -> None:
        self.git_output("remote", "add", "origin", str(useagent.ROOT))
        self.git_output("update-ref", f"refs/remotes/origin/{branch}", commit)
        self.git_output("config", f"branch.{branch}.remote", "origin")
        self.git_output("config", f"branch.{branch}.merge", f"refs/heads/{branch}")

    def test_worker_run_invokes_runner_and_accepts_automatic_report(self) -> None:
        self.register_worker("worker-1", "src")
        self.configure_runner(self.reporting_runner())
        task_id = self.new_task("Automatic worker run", "src/runner.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, output, error = self.invoke("worker", "run", "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        self.assertIn(f"{task_id} runner_status=reported result=completed", output)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["status"], "reported")
        self.assertEqual(item["last_result"], "completed")
        self.assertTrue(item["reports"])
        self.assertTrue(any(entry["kind"] == "runner" for entry in item["evidence"]))

    def test_worker_run_requires_configured_runner_without_claiming(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Runner is opt in", "src/manual.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, output, error = self.invoke("worker", "run", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("no configured runner", error)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "assigned")

    def test_worker_run_records_failure_when_runner_omits_report(self) -> None:
        self.register_worker("worker-1", "src")
        self.configure_runner(
            [
                sys.executable,
                "-c",
                "import sys; raise SystemExit(9)",
                "{assignment_path}",
            ]
        )
        task_id = self.new_task("Runner failure", "src/failure.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, output, error = self.invoke("worker", "run", "--agent", "worker-1")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn(f"{task_id} runner_status=reported result=failed", output)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["status"], "reported")
        self.assertEqual(item["last_result"], "failed")
        self.assertEqual(len(item["reports"]), 1)
        self.assertTrue(any(entry["kind"] == "runner" for entry in item["evidence"]))

    def test_runner_output_is_sanitized_bounded_and_spooled_locally(self) -> None:
        self.register_worker("worker-1", "src")
        runner_code = (
            "import sys\n"
            "print('API_KEY=runner-secret-123456789')\n"
            "print('Authorization: Bearer runner-token-123456789')\n"
            "print('postgresql://runner:runner-password@db.example.test/app')\n"
            "print('{\"password\":\"json-password-123456789\",\"token\":\"json-token-123456789\"}')\n"
            "print('-----BEGIN RSA PRIVATE KEY-----')\n"
            "print('MII_RUNNER_PRIVATE_KEY_MATERIAL_123456789')\n"
            "print('-----END RSA PRIVATE KEY-----')\n"
            f"print('O' * {useagent.MAX_DURABLE_OUTPUT_CHARS + 500})\n"
            "print('Cookie: session=runner-cookie-123456789', file=sys.stderr)\n"
            f"print('E' * {useagent.MAX_DURABLE_OUTPUT_CHARS + 500}, file=sys.stderr)\n"
            "raise SystemExit(9)\n"
        )
        self.configure_runner([sys.executable, "-c", runner_code, "{assignment_path}"])
        task_id = self.new_task("Sanitized runner output", "src/safe-runner.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, _, error = self.invoke("worker", "run", "--agent", "worker-1")
        self.assertEqual((code, error), (1, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        runner_entry = next(entry for entry in registry["items"][task_id]["evidence"] if entry["kind"] == "runner")
        evidence_path = useagent.ROOT / runner_entry["value"].split(" ", 1)[0]
        evidence = evidence_path.read_text(encoding="utf-8")
        for secret in (
            "runner-secret-123456789",
            "runner-token-123456789",
            "runner-password",
            "runner-cookie-123456789",
            "json-password-123456789",
            "json-token-123456789",
            "MII_RUNNER_PRIVATE_KEY_MATERIAL_123456789",
        ):
            self.assertNotIn(secret, evidence)
        self.assertIn("provenance: `local`", evidence)
        self.assertIn(f"budget_chars: `{useagent.MAX_DURABLE_OUTPUT_CHARS}`", evidence)
        self.assertIn("truncated: `true`", evidence)
        preview_chars = int(
            next(line.split("`", 2)[1] for line in evidence.splitlines() if line.startswith("- preview_chars:"))
        )
        self.assertLessEqual(preview_chars, useagent.MAX_DURABLE_OUTPUT_CHARS)
        spool_rel = next(line.split("`", 2)[1] for line in evidence.splitlines() if line.startswith("- local_spool:"))
        self.assertTrue(spool_rel.startswith("work/.runtime-output/"))
        spool = (useagent.ROOT / spool_rel).read_text(encoding="utf-8")
        for secret in (
            "runner-secret-123456789",
            "runner-token-123456789",
            "runner-password",
            "runner-cookie-123456789",
            "json-password-123456789",
            "json-token-123456789",
            "MII_RUNNER_PRIVATE_KEY_MATERIAL_123456789",
        ):
            self.assertNotIn(secret, spool)
        ignore_check = subprocess.run(
            ["git", "check-ignore", "--no-index", "work/.runtime-output/example.md"],
            cwd=self.original_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ignore_check.returncode, 0, ignore_check.stderr)

    def test_runtime_spool_cannot_overlap_committable_evidence(self) -> None:
        config = useagent.load_config()
        config["paths"]["runtime_spool"] = config["paths"]["evidence"]
        errors: list[str] = []
        useagent.validate_config(config, errors)
        self.assertIn("config.paths.runtime_spool must not overlap config.paths.evidence", errors)

    def test_worker_run_times_out_and_records_failure_evidence(self) -> None:
        self.register_worker("worker-1", "src")
        self.configure_runner(
            [
                sys.executable,
                "-c",
                "import time; time.sleep(2)",
                "{assignment_path}",
            ],
            timeout_seconds=1,
        )
        task_id = self.new_task("Runner timeout", "src/timeout.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))

        code, output, error = self.invoke("worker", "run", "--agent", "worker-1")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn(f"{task_id} runner_status=reported result=failed", output)
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["last_result"], "failed")
        runner_evidence = [entry for entry in item["evidence"] if entry["kind"] == "runner"]
        self.assertEqual(len(runner_evidence), 1)
        evidence_path = useagent.ROOT / runner_evidence[0]["value"].split(" ", 1)[0]
        self.assertIn("returncode: `124`", evidence_path.read_text(encoding="utf-8"))

    def test_worker_run_wait_is_bounded_and_returns_no_task(self) -> None:
        self.register_worker("worker-1", "src")
        self.configure_runner(self.reporting_runner())
        code, output, error = self.invoke(
            "worker",
            "run",
            "--agent",
            "worker-1",
            "--wait-seconds",
            "0.1",
            "--poll-seconds",
            "0.1",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "NO_TASK")

    def test_agent_register_persists_argv_runner_contract(self) -> None:
        code, output, error = self.invoke(
            "agent",
            "register",
            "--id",
            "runner-worker",
            "--role",
            "worker",
            "--scope",
            "src",
            "--runner-arg",
            sys.executable,
            "--runner-arg=-c",
            "--runner-arg",
            "print('runner')",
            "--runner-arg",
            "{assignment_path}",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertIn("runner-worker", output)
        config = useagent.load_config()
        runner = config["agents"][0]["runner"]
        self.assertEqual(runner["command"][-1], "{assignment_path}")
        self.assertEqual(runner["timeout_seconds"], useagent.DEFAULT_RUNNER_TIMEOUT_SECONDS)

    def test_validator_rejects_unsafe_runner_shape(self) -> None:
        self.register_worker("worker-1", "src")
        config = useagent.load_config()
        config["agents"][0]["runner"] = {
            "command": ["python", "adapter.py"],
            "timeout_seconds": 0,
        }
        errors: list[str] = []
        useagent.validate_config(config, errors)
        self.assertTrue(any("must include {assignment_path}" in error for error in errors))
        config["agents"][0]["runner"]["command"].append("{assignment_path}")
        errors = []
        useagent.validate_config(config, errors)
        self.assertTrue(any("between 1 and" in error for error in errors))

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

    def test_validator_rejects_malformed_agent_capabilities(self) -> None:
        self.register_worker("worker-1", ".")
        config = useagent.load_config()
        config["agents"][0]["capabilities"] = [["nested"]]
        errors: list[str] = []
        useagent.validate_config(config, errors)
        self.assertIn(
            "capabilities must be an array of non-empty strings for agent worker-1",
            errors,
        )

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
        self.assertIn(f"{task_id} is done without non-empty review evidence", errors)

    def test_update_cannot_bypass_claim(self) -> None:
        task_id = self.new_task("Claimed only through the CLI", "src/claim.py")
        code, _, error = self.invoke("task", "update", task_id, "--status", "in_progress", "--agent", "worker-1")
        self.assertEqual(code, 2)
        self.assertIn("task claim", error)

    def test_assigned_task_requires_claim_before_activation(self) -> None:
        self.register_worker("worker-1", ".")
        task_id = self.new_task("Claim before activation", "src/activation.py")

        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_before["items"][task_id]["status"], "assigned")
        self.assertEqual(registry_before["items"][task_id]["assigned_to"], "worker-1")

        code, _, error = self.invoke(
            "task", "update", task_id, "--status", "in_progress", "--agent", "worker-1"
        )
        self.assertEqual(code, 2)
        self.assertIn("task claim", error)
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][task_id], registry_before["items"][task_id])

        code, _, error = self.invoke("worker", "pull", "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][task_id]["status"], "in_progress")

    def test_task_report_requires_activation(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Report after activation", "src/report-activation.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        report_paths_before = sorted((useagent.ROOT / "work" / "reports" / "inbox").glob("*.md"))

        code, _, error = self.invoke(
            "task",
            "report",
            task_id,
            "--agent",
            "worker-1",
            "--result",
            "completed",
            "--summary",
            "Must not bypass activation",
            "--next-action",
            "Pull the assignment first",
            "--file",
            "src/report-activation.py",
            "--check",
            "should not be accepted",
        )
        self.assertEqual(code, 2)
        self.assertIn("worker must claim or pull before reporting", error)
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][task_id], registry_before["items"][task_id])
        self.assertEqual(sorted((useagent.ROOT / "work" / "reports" / "inbox").glob("*.md")), report_paths_before)

    def test_supervisor_ingest_ignores_report_for_unactivated_task(self) -> None:
        self.register_worker("worker-1", "src")
        task_id = self.new_task("Ignore unactivated report", "src/unactivated-report.py")
        code, _, error = self.invoke("supervisor", "dispatch")
        self.assertEqual((code, error), (0, ""))
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        fake_report = useagent.ROOT / "work" / "reports" / "inbox" / f"{task_id}-unactivated.md"
        fake_report.write_text(
            "\n".join(
                [
                    "---",
                    "type: useagent-worker-report",
                    f"task_id: {task_id}",
                    "agent: worker-1",
                    "result: completed",
                    "files: [\"src/unactivated-report.py\"]",
                    "checks: [\"forged\"]",
                    "---",
                    "",
                    "# Forged report",
                    "",
                    "This must not enter the ledger before activation.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        code, output, error = self.invoke("supervisor", "ingest")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "no new reports")
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][task_id], registry_before["items"][task_id])
        state = useagent.load_supervisor_state(useagent.load_config())
        self.assertNotIn(useagent.rel(fake_report), state.get("ingested_reports", []))

    def test_administrative_transitions_require_review_role(self) -> None:
        self.register_worker("worker-1", ".")
        self.register_reviewer()
        task_id = self.new_task("Administrative lifecycle", "src/administrative.py")
        registry_before = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))

        for status in ("blocked", "cancelled"):
            code, _, error = self.invoke(
                "task", "update", task_id, "--status", status, "--agent", "worker-1"
            )
            self.assertEqual(code, 2)
            self.assertIn("not authorized for review actions", error)
            registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
            self.assertEqual(registry["items"][task_id], registry_before["items"][task_id])

        code, _, error = self.invoke(
            "task", "update", task_id, "--status", "blocked", "--agent", "reviewer"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task", "update", task_id, "--status", "planned", "--agent", "reviewer"
        )
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task", "update", task_id, "--status", "cancelled", "--agent", "reviewer"
        )
        self.assertEqual((code, error), (0, ""))

        blocked_id = self.new_task("Worker blocked handover", "src/blocked.py")
        code, _, error = self.invoke("task", "claim", blocked_id, "--agent", "worker-1")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            blocked_id,
            "--agent",
            "worker-1",
            "--result",
            "blocked",
            "--summary",
            "Waiting for an external dependency",
            "--next-action",
            "Review blocker and decide whether to retry",
            "--file",
            "src/blocked.py",
            "--check",
            "reproduction recorded",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["items"][blocked_id]["status"], "blocked")
        self.assertEqual(len(registry["items"][blocked_id]["reports"]), 1)

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

    def test_evidence_provenance_is_typed_and_worker_reports_preserve_it(self) -> None:
        evidence_task = self.new_task("Typed evidence", "docs/evidence.md")
        code, _, error = self.invoke(
            "task",
            "evidence",
            evidence_task,
            "--kind",
            "smoke",
            "--value",
            "Named production endpoint returned 200",
            "--provenance",
            "live",
            "--source",
            "https://example.invalid/health",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        entry = registry["items"][evidence_task]["evidence"][-1]
        self.assertEqual(entry["provenance"], "live")
        self.assertEqual(entry["source"], "https://example.invalid/health")
        self.assertTrue(entry["recorded_at"])

        evidence_before = list(registry["items"][evidence_task]["evidence"])
        code, _, error = self.invoke(
            "task",
            "evidence",
            evidence_task,
            "--kind",
            "smoke",
            "--value",
            "Unknown provenance must fail",
            "--provenance",
            "invented",
            "--source",
            "test",
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid evidence provenance", error)
        registry_after = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry_after["items"][evidence_task]["evidence"], evidence_before)
        code, _, error = self.invoke(
            "task",
            "evidence",
            evidence_task,
            "--kind",
            "smoke",
            "--value",
            "Reserved legacy label must fail for new CLI evidence",
            "--provenance",
            "legacy",
            "--source",
            "test",
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid evidence provenance", error)
        malformed_registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        malformed_registry["items"][evidence_task]["evidence"].append(
            {"kind": "bad", "value": "untrusted", "provenance": "invented", "source": "test"}
        )
        validation_errors: list[str] = []
        useagent.validate_registry(malformed_registry, validation_errors)
        self.assertTrue(any("invalid evidence provenance" in value for value in validation_errors))

        self.register_worker("provenance-worker", "src")
        report_task = self.new_task("Provenance report", "src/provenance.py")
        code, _, error = self.invoke("task", "claim", report_task, "--agent", "provenance-worker")
        self.assertEqual((code, error), (0, ""))
        code, _, error = self.invoke(
            "task",
            "report",
            report_task,
            "--agent",
            "provenance-worker",
            "--result",
            "completed",
            "--summary",
            "Replay completed without external provider execution",
            "--next-action",
            "Review the simulation evidence",
            "--provenance",
            "simulation",
            "--source",
            "examples/multi-runtime-conformance/run_conformance.py",
            "--file",
            "src/provenance.py",
            "--check",
            "replay: pass",
        )
        self.assertEqual((code, error), (0, ""))
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        entries = registry["items"][report_task]["evidence"]
        report_entry = next(entry for entry in entries if entry["kind"] == "worker-report")
        self.assertEqual(report_entry["provenance"], "simulation")
        self.assertEqual(report_entry["source"], "examples/multi-runtime-conformance/run_conformance.py")
        check_entry = next(entry for entry in entries if entry["kind"] == "check")
        self.assertEqual(check_entry["provenance"], "simulation")
        report_path = useagent.ROOT / registry["items"][report_task]["reports"][0]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("provenance: simulation", report_text)
        self.assertIn("source: examples/multi-runtime-conformance/run_conformance.py", report_text)

    def test_malformed_external_report_provenance_is_ignored_safely(self) -> None:
        self.register_worker("malformed-provenance", "src")
        task_id = self.new_task("Reject malformed provenance", "src/malformed.py")
        code, _, error = self.invoke("task", "claim", task_id, "--agent", "malformed-provenance")
        self.assertEqual((code, error), (0, ""))
        report_path = useagent.ROOT / "work" / "reports" / "inbox" / f"{task_id}-malformed-provenance.md"
        report_path.write_text(
            "---\n"
            "type: useagent-worker-report\n"
            f"task_id: {task_id}\n"
            "agent: malformed-provenance\n"
            "result: completed\n"
            "provenance: invented\n"
            "source: external-runner\n"
            "files: [\"src/malformed.py\"]\n"
            "---\n\ninvalid provenance\n",
            encoding="utf-8",
        )
        code, output, error = self.invoke("supervisor", "ingest")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "no new reports")
        registry = json.loads(useagent.REGISTRY.read_text(encoding="utf-8"))
        item = registry["items"][task_id]
        self.assertEqual(item["status"], "in_progress")
        self.assertEqual(item["reports"], [])

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

    def test_supervisor_report_freshness_marker_and_safe_check(self) -> None:
        self.new_task("Freshness marker", "docs/freshness.md")
        code, _, error = self.invoke("supervisor", "report")
        self.assertEqual((code, error), (0, ""))
        report_path = useagent.ROOT / "work" / "SUPERVISOR_REPORT.md"
        report = report_path.read_text(encoding="utf-8")
        self.assertRegex(report, r"(?m)^<!-- useagent-report: registry_sha256=[0-9a-f]{64} -->$")
        self.assertIn("Registry revision", report)

        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("freshness=fresh", output)

        self.new_task("Make report stale", "docs/stale.md")
        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn("freshness=stale", output)
        code, output, error = self.invoke("context", "--max-chars", "10000")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Freshness:** stale", output)
        self.assertIn("not current", output)

        report_path.unlink()
        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn("freshness=missing", output)

        report_path.write_text("# Missing marker\n", encoding="utf-8")
        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn("freshness=unknown", output)
        self.assertIn("missing or malformed", output)

        report_path.write_text("<!-- useagent-report: registry_sha256=not-a-revision -->\n", encoding="utf-8")
        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn("freshness=unknown", output)

    def test_supervisor_report_uses_safe_repository_relative_configured_path(self) -> None:
        config = useagent.load_config()
        config["paths"]["supervisor_report"] = "work/reports/custom-supervisor.md"
        useagent.save_config(config)
        self.new_task("Custom report path", "docs/custom-report.md")

        code, output, error = self.invoke("supervisor", "report")
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output.strip(), "work/reports/custom-supervisor.md")
        self.assertTrue((useagent.ROOT / "work" / "reports" / "custom-supervisor.md").is_file())

        code, output, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("freshness=fresh", output)

        config["paths"]["supervisor_report"] = "../outside.md"
        useagent.save_config(config)
        code, _, error = self.invoke("supervisor", "report", "--check")
        self.assertEqual(code, 2)
        self.assertIn("leaves project root", error)

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
        self.assertTrue(state["last_qa"]["source_fingerprint"])
        self.assertEqual(state["last_qa"]["source_dirty_state"], "unknown")
        self.assertTrue(state["last_qa"]["qa_config_fingerprint"])
        self.assertEqual(len(state["last_qa"]["executed_checks"]), 1)
        self.assertTrue((useagent.ROOT / state["last_qa"]["evidence"]).exists())

        config["supervisor"]["qa_commands"] = ['python -c "raise SystemExit(1)"']
        useagent.save_config(config)
        code, output, error = self.invoke("supervisor", "cycle", "--run-qa")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("create a scoped debug task", output)

    def test_qa_output_is_sanitized_bounded_and_spooled_locally(self) -> None:
        qa_script = useagent.ROOT / "qa-output.py"
        qa_script.write_text(
            "import sys\n"
            "print('API_KEY=qa-secret-123456789')\n"
            f"print('Q' * {useagent.MAX_DURABLE_OUTPUT_CHARS + 500})\n"
            "print('Cookie: session=qa-cookie-123456789', file=sys.stderr)\n"
            f"print('W' * {useagent.MAX_DURABLE_OUTPUT_CHARS + 500}, file=sys.stderr)\n",
            encoding="utf-8",
        )
        config = useagent.load_config()
        config["supervisor"]["qa_commands"] = [f'"{sys.executable}" "{qa_script}"']
        useagent.save_config(config)

        code, output, error = self.invoke("supervisor", "qa")
        self.assertEqual((code, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["provenance"], "local")
        self.assertEqual(result["source"], "configured supervisor.qa_commands")
        command_result = result["commands"][0]
        self.assertGreater(command_result["stdout"]["captured_chars"], useagent.MAX_DURABLE_OUTPUT_CHARS)
        self.assertTrue(command_result["stdout"]["truncated"])
        self.assertLessEqual(command_result["stdout"]["preview_chars"], useagent.MAX_DURABLE_OUTPUT_CHARS)
        self.assertGreater(command_result["stderr"]["captured_chars"], useagent.MAX_DURABLE_OUTPUT_CHARS)
        self.assertTrue(command_result["stderr"]["truncated"])
        self.assertLessEqual(command_result["stderr"]["preview_chars"], useagent.MAX_DURABLE_OUTPUT_CHARS)
        for secret in ("qa-secret-123456789", "qa-cookie-123456789"):
            self.assertNotIn(secret, output)

        evidence_path = useagent.ROOT / result["evidence"]
        evidence = evidence_path.read_text(encoding="utf-8")
        self.assertIn("provenance: `local`", evidence)
        self.assertIn("output_budget_chars", evidence)
        for secret in ("qa-secret-123456789", "qa-cookie-123456789"):
            self.assertNotIn(secret, evidence)
        spool_rel = result["local_spool"]
        self.assertTrue(spool_rel.startswith("work/.runtime-output/"))
        self.assertTrue((useagent.ROOT / spool_rel).is_file())
        self.assertNotIn("qa-secret-123456789", (useagent.ROOT / spool_rel).read_text(encoding="utf-8"))

    def test_qa_source_fingerprint_is_valid_when_source_is_unchanged(self) -> None:
        config, result = self.successful_qa()
        gates, _ = useagent.production_snapshot(config, self.release_data_with_done_task(), {"last_qa": result})
        self.assertEqual(dict(gates)["qa"], "pass")
        self.assertEqual(dict(gates)["qa_source_state"], "pass")

    def test_qa_source_fingerprint_stales_when_untracked_source_changes(self) -> None:
        config, result = self.successful_qa()
        source = useagent.ROOT / "src" / "article.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("version one", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "QA_STALE")
        gates, ready = useagent.production_snapshot(config, self.release_data_with_done_task(), {"last_qa": result})
        self.assertEqual(dict(gates)["qa_source_state"], "QA_STALE")
        self.assertEqual(dict(gates)["qa"], "fail")
        self.assertFalse(ready)

    def test_qa_source_fingerprint_stales_when_test_file_changes(self) -> None:
        config, result = self.successful_qa()
        test_file = useagent.ROOT / "tests" / "test_article.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("assert True", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "QA_STALE")

    def test_qa_source_fingerprint_stales_when_qa_contract_changes(self) -> None:
        config, result = self.successful_qa()
        changed_config = self.configure_qa('python -c "print(\'qa-contract-changed\')"')
        self.assertNotEqual(config["supervisor"]["qa_commands"], changed_config["supervisor"]["qa_commands"])
        self.assertEqual(useagent.validate_qa_source(changed_config, {"last_qa": result})["status"], "QA_STALE")

    def test_qa_fingerprint_records_dirty_git_source_state(self) -> None:
        source = useagent.ROOT / "src" / "dirty.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("baseline", encoding="utf-8")
        config = self.configure_qa()
        self.initialize_git_baseline()
        source.write_text("working tree change", encoding="utf-8")

        result = useagent.run_qa(config, "dirty-source-test")

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["source_vcs"], "git")
        self.assertEqual(result["source_dirty_state"], "dirty")
        self.assertTrue(result["source_dirty"])
        self.assertEqual(len(result["source_head_sha"]), 40)
        self.assertGreater(result["source_dirty_path_count"], 0)
        source.write_text("second working tree change", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "QA_STALE")

    def test_clean_qa_becomes_stale_when_git_dirty_state_changes(self) -> None:
        source = useagent.ROOT / "src" / "clean.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("baseline", encoding="utf-8")
        config = self.configure_qa()
        self.initialize_git_baseline()

        result = useagent.run_qa(config, "clean-source-test")

        self.assertEqual(result["source_vcs"], "git")
        self.assertEqual(result["source_dirty_state"], "clean")
        source.write_text("now dirty", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "QA_STALE")

    def test_volatile_control_plane_updates_do_not_stale_qa(self) -> None:
        config, result = self.successful_qa()
        generated_paths = (
            "work/registry.json",
            "work/items/generated.md",
            "work/reports/generated.md",
            "work/checkpoints/generated.md",
            "work/evidence/generated.md",
            "work/.runtime-output/generated.md",
            "work/SUPERVISOR_REPORT.md",
            "work/supervisor/generated.json",
        )
        for relative in generated_paths:
            path = useagent.ROOT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("control-plane update", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "valid")

    def test_qa_rerun_on_new_source_state_restores_validity(self) -> None:
        config, first = self.successful_qa()
        source = useagent.ROOT / "src" / "rerun.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("new source state", encoding="utf-8")
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": first})["status"], "QA_STALE")

        second = useagent.run_qa(config, "rerun-source-test")

        self.assertNotEqual(first["source_fingerprint"], second["source_fingerprint"])
        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": second})["status"], "valid")

    def test_release_durability_passes_for_clean_committed_git_source(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        result = useagent.run_qa(config, "durability-clean-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["vcs"], "git")
        self.assertEqual(snapshot["dirty_state"], "clean")
        self.assertEqual(snapshot["untracked_path_count"], 0)
        self.assertEqual(snapshot["qa_source_state"], "valid")
        self.assertEqual(snapshot["upstream_state"], "none")
        self.assertEqual(snapshot["upstream_relation"], "none")

    def test_dirty_tracked_source_keeps_qa_valid_but_fails_release_durability(self) -> None:
        source = useagent.ROOT / "src" / "dirty-release.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("baseline", encoding="utf-8")
        config = self.configure_qa()
        self.initialize_git_baseline()
        source.write_text("dirty", encoding="utf-8")
        result = useagent.run_qa(config, "durability-dirty-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(useagent.validate_qa_source(config, {"last_qa": result})["status"], "valid")
        self.assertEqual(snapshot["status"], "fail")
        self.assertEqual(snapshot["dirty_state"], "dirty")
        self.assertEqual(snapshot["qa_source_state"], "valid")

    def test_staged_source_change_fails_release_durability(self) -> None:
        source = useagent.ROOT / "src" / "staged-release.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("baseline", encoding="utf-8")
        config = self.configure_qa()
        self.initialize_git_baseline()
        source.write_text("staged", encoding="utf-8")
        self.git_output("add", "src/staged-release.py")
        result = useagent.run_qa(config, "durability-staged-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "fail")
        self.assertEqual(snapshot["dirty_state"], "dirty")
        self.assertGreater(snapshot["dirty_path_count"], 0)

    def test_nonignored_untracked_source_fails_release_durability(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        source = useagent.ROOT / "src" / "untracked-release.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("untracked", encoding="utf-8")
        result = useagent.run_qa(config, "durability-untracked-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "fail")
        self.assertEqual(snapshot["untracked_path_count"], 1)

    def test_volatile_control_plane_writes_do_not_fail_release_durability(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        result = useagent.run_qa(config, "durability-volatile-test")
        volatile = useagent.ROOT / "work" / "evidence" / "volatile-only.md"
        volatile.write_text("runtime evidence", encoding="utf-8")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["dirty_state"], "clean")
        self.assertEqual(snapshot["untracked_path_count"], 0)

    def test_convenience_supervisor_report_is_volatile_for_release_durability(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        result = useagent.run_qa(config, "durability-report-write-test")
        report_path = useagent.ROOT / "work" / "SUPERVISOR_REPORT.md"
        report_path.write_text("generated convenience report", encoding="utf-8")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["dirty_state"], "clean")
        self.assertEqual(snapshot["untracked_path_count"], 0)

    def test_commit_after_qa_requires_rerun_then_durability_passes(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        first = useagent.run_qa(config, "durability-commit-transition-test")
        first_snapshot = useagent.release_durability_snapshot(config, {"last_qa": first})
        self.assertEqual(first_snapshot["status"], "pass")

        marker = useagent.ROOT / "work" / "evidence" / "post-qa-commit.md"
        marker.write_text("post QA bookkeeping", encoding="utf-8")
        self.git_output("add", "work/evidence/post-qa-commit.md")
        self.git_output("commit", "-qm", "post QA bookkeeping")
        stale = useagent.release_durability_snapshot(config, {"last_qa": first})

        self.assertEqual(stale["status"], "fail")
        self.assertEqual(stale["qa_source_state"], "QA_STALE")
        self.assertNotEqual(first["source_fingerprint"], stale["fingerprint"])

        second = useagent.run_qa(config, "durability-commit-rerun-test")
        second_snapshot = useagent.release_durability_snapshot(config, {"last_qa": second})
        self.assertEqual(second_snapshot["status"], "pass")
        self.assertEqual(second_snapshot["qa_source_state"], "valid")

    def test_non_git_workspace_is_explicitly_degraded(self) -> None:
        config, result = self.successful_qa()

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})
        gates, ready = useagent.production_snapshot(config, self.release_data_with_done_task(), {"last_qa": result})

        self.assertEqual(snapshot["vcs"], "filesystem")
        self.assertEqual(snapshot["status"], "manual")
        self.assertEqual(snapshot["upstream_state"], "not_applicable")
        self.assertEqual(dict(gates)["release_source_durability"], "manual")
        self.assertFalse(ready)

    def test_supervisor_report_records_release_provenance(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        result = useagent.run_qa(config, "durability-report-test")
        data = self.release_data_with_done_task()
        data["items"]["UA-9999"] = {
            "id": "UA-9999",
            "title": "Durability report fixture",
            "status": "done",
            "evidence": [],
            "reports": [],
        }
        report, _ = useagent.build_supervisor_report(
            config,
            data,
            {"last_qa": result},
            "durability-report-cycle",
            [],
            [],
            result,
        )

        self.assertIn("## Release source", report)
        self.assertIn(f"- source_fingerprint: `{result['source_fingerprint']}`", report)
        self.assertIn(f"- qa_source_fingerprint: `{result['source_fingerprint']}`", report)
        self.assertIn(f"- qa_config_fingerprint: `{result['qa_config_fingerprint']}`", report)
        self.assertIn("- local_durability: `pass`", report)
        self.assertIn("- upstream_relation: `none`", report)
        self.assertIn("`release_source_durability`: `pass`", report)

    def test_upstream_metadata_is_local_and_does_not_require_origin_sync(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        branch = self.git_output("symbolic-ref", "--quiet", "--short", "HEAD")
        previous = self.git_output("rev-parse", "HEAD")
        source = useagent.ROOT / "src" / "ahead.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("ahead", encoding="utf-8")
        self.git_output("add", "src/ahead.py")
        self.git_output("commit", "-qm", "ahead commit")
        self.configure_tracking_ref(branch, previous)
        result = useagent.run_qa(config, "durability-ahead-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["upstream_state"], "known")
        self.assertEqual(snapshot["upstream_relation"], "ahead")
        self.assertEqual(snapshot["ahead"], 1)
        self.assertEqual(snapshot["behind"], 0)

    def test_configured_but_unavailable_upstream_is_explicitly_unknown(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        branch = self.git_output("symbolic-ref", "--quiet", "--short", "HEAD")
        self.git_output("remote", "add", "origin", str(useagent.ROOT))
        self.git_output("config", f"branch.{branch}.remote", "origin")
        self.git_output("config", f"branch.{branch}.merge", f"refs/heads/{branch}")
        result = useagent.run_qa(config, "durability-unknown-upstream-test")

        snapshot = useagent.release_durability_snapshot(config, {"last_qa": result})

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["upstream_state"], "unknown")
        self.assertEqual(snapshot["upstream_relation"], "unknown")
        self.assertIsNone(snapshot["ahead"])
        self.assertIsNone(snapshot["behind"])

    def test_upstream_metadata_reports_behind_and_diverged_without_failing_local_durability(self) -> None:
        config = self.configure_qa()
        self.initialize_git_baseline()
        branch = self.git_output("symbolic-ref", "--quiet", "--short", "HEAD")
        base = self.git_output("rev-parse", "HEAD")
        base_tree = self.git_output("rev-parse", "HEAD^{tree}")
        remote_only = self.git_output("commit-tree", base_tree, "-p", base, "-m", "remote-only")
        self.configure_tracking_ref(branch, remote_only)
        behind_result = useagent.run_qa(config, "durability-behind-test")
        behind = useagent.release_durability_snapshot(config, {"last_qa": behind_result})

        self.assertEqual(behind["status"], "pass")
        self.assertEqual(behind["upstream_relation"], "behind")
        self.assertEqual(behind["ahead"], 0)
        self.assertEqual(behind["behind"], 1)

        source = useagent.ROOT / "src" / "diverged.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("local-only", encoding="utf-8")
        self.git_output("add", "src/diverged.py")
        self.git_output("commit", "-qm", "local-only")
        local_base = self.git_output("rev-parse", "HEAD~1")
        local_base_tree = self.git_output("rev-parse", "HEAD~1^{tree}")
        remote_diverged = self.git_output("commit-tree", local_base_tree, "-p", local_base, "-m", "remote-diverged")
        self.git_output("update-ref", f"refs/remotes/origin/{branch}", remote_diverged)
        diverged_result = useagent.run_qa(config, "durability-diverged-test")
        diverged = useagent.release_durability_snapshot(config, {"last_qa": diverged_result})

        self.assertEqual(diverged["status"], "pass")
        self.assertEqual(diverged["upstream_relation"], "diverged")
        self.assertEqual(diverged["ahead"], 1)
        self.assertEqual(diverged["behind"], 1)

    def test_legacy_pass_without_source_fingerprint_is_stale(self) -> None:
        config = self.configure_qa()
        gates, ready = useagent.production_snapshot(
            config,
            self.release_data_with_done_task(),
            {"last_qa": {"status": "pass"}},
        )
        self.assertEqual(dict(gates)["qa_source_state"], "QA_STALE")
        self.assertEqual(dict(gates)["qa"], "fail")
        self.assertFalse(ready)

    def test_production_snapshot_checks_operational_readiness_files(self) -> None:
        (useagent.ROOT / "docs").mkdir(parents=True, exist_ok=True)
        (useagent.ROOT / "docs" / "operations.md").write_text("Operational runbook", encoding="utf-8")
        (useagent.ROOT / "docs" / "rollback.md").write_text("Rollback plan", encoding="utf-8")
        config = useagent.load_config()
        config["supervisor"]["operational_readiness_files"] = ["docs/operations.md", "docs/rollback.md"]
        config["supervisor"]["qa_commands"] = ['python -c "print(\'qa-pass\')"']
        useagent.save_config(config)
        qa_result = useagent.run_qa(config, "readiness-test")
        data = useagent.load_registry()
        data["items"]["UA-9999"] = {"status": "done"}
        state = {"last_qa": qa_result}
        gates, ready = useagent.production_snapshot(config, data, state)
        self.assertEqual(dict(gates)["operational_rollback_notes"], "pass")
        self.assertEqual(dict(gates)["release_source_durability"], "manual")
        self.assertFalse(ready)

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
