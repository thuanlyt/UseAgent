#!/usr/bin/env python3
"""UseAgent supervisor control plane.

The CLI is deliberately small and dependency-free. It provides a durable
file protocol for a supervisor model and worker agents:

    supervisor -> assignment .md -> worker mailbox
    worker -> report .md -> supervisor report/completed log

JSON is the machine-readable state; Markdown is the human- and model-readable
handoff surface. The CLI never edits application code and never grants deploy
authority.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "work" / "registry.json"
CONFIG = ROOT / "useagent.config.json"
LOCK = ROOT / "work" / ".state.lock"

ACTIVE_WRITER_STATUSES = {"assigned", "in_progress"}
VALID_STATUSES = {
    "planned",
    "assigned",
    "in_progress",
    "reported",
    "needs_review",
    "done",
    "blocked",
    "cancelled",
}
VALID_LEVELS = {"L0", "L1", "L2", "L3", "L4"}
VALID_AGENT_STATUSES = {"available", "busy", "paused", "offline"}


DEFAULT_CONFIG: dict[str, Any] = {
    "version": 2,
    "paths": {
        "agent_root": "work/agents",
        "reports_inbox": "work/reports/inbox",
        "reports_archive": "work/reports/archive",
        "reports_index": "work/reports/REPORTS.md",
        "outbox": "work/outbox",
        "completed_tasks": "work/completed/COMPLETED.md",
        "supervisor_report": "work/SUPERVISOR_REPORT.md",
        "supervisor_cycle": "work/supervisor/LATEST_CYCLE.md",
        "supervisor_state": "work/supervisor/state.json",
        "checkpoints": "work/checkpoints",
        "evidence": "work/evidence",
    },
    "supervisor": {
        "max_assignments_per_cycle": 4,
        "run_qa_each_cycle": False,
        "auto_dispatch": True,
        "qa_timeout_seconds": 900,
        "qa_commands": [],
        "operational_readiness_files": ["docs/operations.md", "docs/autopilot.md"],
        "production_gates": [
            "All acceptance criteria are evidenced",
            "Focused and integration tests pass",
            "No open P0/P1 review finding",
            "Operational and rollback notes exist",
        ],
    },
    "agents": [],
}


class UseAgentError(RuntimeError):
    """Expected user-facing error from the control plane."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


@contextmanager
def state_lock(timeout: float = 30.0) -> Iterator[None]:
    """Acquire a short-lived exclusive lock using create-if-absent semantics."""

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    payload = json.dumps({"pid": os.getpid(), "created_at": now_iso()})
    while True:
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, payload.encode("utf-8"))
            finally:
                os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() - started >= timeout:
                try:
                    owner = LOCK.read_text(encoding="utf-8")
                except OSError:
                    owner = "unknown owner"
                raise UseAgentError(f"state lock is busy: {owner}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


def safe_repo_path(value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise UseAgentError(f"configured path leaves project root: {value}") from exc
    return candidate


def load_config() -> dict[str, Any]:
    if not CONFIG.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        value = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UseAgentError(f"invalid JSON in {rel(CONFIG)}: {exc}") from exc
    if not isinstance(value, dict):
        raise UseAgentError(f"{rel(CONFIG)} must contain a JSON object")
    merged = copy.deepcopy(DEFAULT_CONFIG)
    merged.update({key: value[key] for key in value if key not in {"paths", "supervisor"}})
    merged["paths"].update(value.get("paths", {}))
    merged["supervisor"].update(value.get("supervisor", {}))
    if not isinstance(merged.get("agents"), list):
        raise UseAgentError("config.agents must be an array")
    return merged


def save_config(config: dict[str, Any]) -> None:
    atomic_write(CONFIG, json.dumps(config, indent=2, ensure_ascii=False) + "\n")


def path_for(config: dict[str, Any], key: str) -> Path:
    value = config.get("paths", {}).get(key, DEFAULT_CONFIG["paths"].get(key))
    if not value:
        raise UseAgentError(f"missing configured path: {key}")
    return safe_repo_path(value)


def ensure_layout() -> None:
    for directory in (
        ROOT / ".agents" / "skills",
        ROOT / ".codex" / "agents",
        ROOT / "knowledge",
        ROOT / "work" / "items",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    config = load_config()
    for key in ("agent_root", "reports_inbox", "reports_archive", "outbox", "checkpoints", "evidence"):
        path_for(config, key).mkdir(parents=True, exist_ok=True)
    for key in ("completed_tasks", "reports_index", "supervisor_report", "supervisor_cycle", "supervisor_state"):
        path_for(config, key).parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY.exists():
        atomic_write(REGISTRY, json.dumps({"version": 1, "updated_at": None, "items": {}}, indent=2) + "\n")
    if not CONFIG.exists():
        save_config(config)


def load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        raise UseAgentError(f"missing {rel(REGISTRY)}; run init first")
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UseAgentError(f"invalid JSON in {rel(REGISTRY)}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        raise UseAgentError(f"{rel(REGISTRY)} must contain an object named items")
    return data


def save_registry(data: dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    atomic_write(REGISTRY, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def item_path(task_id: str) -> Path:
    return ROOT / "work" / "items" / f"{task_id}.md"


def normalize_scope(value: str) -> str:
    value = value.replace("\\", "/").strip()
    value = re.sub(r"/+$", "", value)
    return value or "."


def scope_overlaps(left: str, right: str) -> bool:
    left_parts = [part for part in normalize_scope(left).split("/") if part not in ("", ".")]
    right_parts = [part for part in normalize_scope(right).split("/") if part not in ("", ".")]
    if not left_parts or not right_parts:
        return True
    shortest = min(len(left_parts), len(right_parts))
    return left_parts[:shortest] == right_parts[:shortest]


def scope_within(scope: str, allowed: str) -> bool:
    allowed_parts = [part for part in normalize_scope(allowed).split("/") if part not in ("", ".")]
    scope_parts = [part for part in normalize_scope(scope).split("/") if part not in ("", ".")]
    return not allowed_parts or scope_parts[: len(allowed_parts)] == allowed_parts


def active_scope_conflict(data: dict[str, Any], candidate: dict[str, Any], ignore_id: str | None = None) -> dict[str, Any] | None:
    for other_id, other in data["items"].items():
        if other_id == ignore_id or other.get("status") not in ACTIVE_WRITER_STATUSES:
            continue
        if any(scope_overlaps(left, right) for left in candidate.get("scope", []) for right in other.get("scope", [])):
            return other
    return None


def next_id(items: dict[str, Any]) -> str:
    numbers = []
    for key in items:
        match = re.fullmatch(r"UA-(\d{4,})", key)
        if match:
            numbers.append(int(match.group(1)))
    return f"UA-{max(numbers, default=0) + 1:04d}"


def get_item(data: dict[str, Any], task_id: str) -> dict[str, Any]:
    item = data["items"].get(task_id)
    if not isinstance(item, dict):
        raise UseAgentError(f"unknown task: {task_id}")
    return item


def dependencies_done(data: dict[str, Any], item: dict[str, Any]) -> bool:
    return all(data["items"].get(dep, {}).get("status") == "done" for dep in item.get("depends_on", []))


def agent_config(config: dict[str, Any], agent_id: str) -> dict[str, Any]:
    for agent in config.get("agents", []):
        if agent.get("id") == agent_id:
            return agent
    raise UseAgentError(f"unknown registered agent: {agent_id}")


def agent_paths(config: dict[str, Any], agent: dict[str, Any]) -> dict[str, Path]:
    base = safe_repo_path(agent.get("directory", str(Path(config["paths"]["agent_root"]) / agent["id"])))
    return {
        "directory": base,
        "inbox": safe_repo_path(agent.get("inbox", base / "INBOX.md")),
        "report": safe_repo_path(agent.get("report", base / "REPORT.md")),
        "completed": safe_repo_path(agent.get("completed", base / "COMPLETED.md")),
        "inbox_dir": safe_repo_path(agent.get("inbox_dir", base / "inbox")),
    }


def append_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        atomic_write(path, content)


def sync_item_frontmatter(item: dict[str, Any]) -> None:
    """Refresh machine-owned header without overwriting agent notes."""

    path = item_path(item["id"])
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return
    values = {
        "id": item["id"],
        "title": json.dumps(item["title"], ensure_ascii=False),
        "level": item["level"],
        "status": item["status"],
        "owner": item["owner"],
        "assigned_to": item.get("assigned_to") or "null",
        "scope": json.dumps(item.get("scope", []), ensure_ascii=False),
        "depends_on": json.dumps(item.get("depends_on", []), ensure_ascii=False),
    }
    lines = []
    seen: set[str] = set()
    for line in match.group(1).splitlines():
        if ":" not in line:
            lines.append(line)
            continue
        key, _ = line.split(":", 1)
        key = key.strip()
        if key in values:
            lines.append(f"{key}: {values[key]}")
            seen.add(key)
        else:
            lines.append(line)
    for key, value in values.items():
        if key not in seen:
            lines.append(f"{key}: {value}")
    atomic_write(path, "---\n" + "\n".join(lines) + "\n---\n" + text[match.end() :])


def append_event(task_id: str, message: str) -> None:
    path = item_path(task_id)
    if path.exists():
        append_markdown(path, f"- {now_iso()} - {message}\n")


def render_item(item: dict[str, Any]) -> str:
    lines = [
        "---",
        f"id: {item['id']}",
        f"title: {json.dumps(item['title'], ensure_ascii=False)}",
        f"level: {item['level']}",
        f"status: {item['status']}",
        f"owner: {item['owner']}",
        f"assigned_to: {item.get('assigned_to') or 'null'}",
        f"scope: {json.dumps(item.get('scope', []), ensure_ascii=False)}",
        f"depends_on: {json.dumps(item.get('depends_on', []), ensure_ascii=False)}",
        "---",
        "",
        f"# {item['title']}",
        "",
        "## Objective",
        "",
        item.get("objective", item["title"]),
        "",
        "## Acceptance criteria",
        "",
    ]
    lines.extend(f"- [ ] {criterion}" for criterion in item.get("acceptance", []))
    lines.extend(["", "## Context to read", "", "- `knowledge/INDEX.md`", "", "## Plan", "", "## Files and evidence", "", "## Blockers", "", "## Handover", "", "## Event log", f"- {item['created_at']} - created by {item['owner']}", ""])
    return "\n".join(lines)


def render_assignment(item: dict[str, Any], agent: dict[str, Any], assignment_path: str) -> str:
    checks = item.get("verification") or ["Run focused tests relevant to the scope"]
    lines = [
        "---",
        "type: useagent-assignment",
        f"task_id: {item['id']}",
        f"agent: {agent['id']}",
        f"created_at: {now_iso()}",
        f"scope: {json.dumps(item.get('scope', []), ensure_ascii=False)}",
        "---",
        "",
        f"# Assignment {item['id']}: {item['title']}",
        "",
        "You are the assigned worker. Use `$useagent-worker` and do not modify files outside the scope below.",
        "",
        "## Objective",
        "",
        item.get("objective", item["title"]),
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{scope}`" for scope in item.get("scope", []))
    lines.extend(["", "## Dependencies", "", ", ".join(item.get("depends_on", [])) or "- none", "", "## Acceptance", ""])
    lines.extend(f"- [ ] {criterion}" for criterion in item.get("acceptance", []))
    lines.extend(["", "## Verification", ""])
    lines.extend(f"- `{check}`" for check in checks)
    lines.extend(
        [
            "",
            "## Read first",
            "",
            "- `AGENTS.md`",
            "- `knowledge/INDEX.md`",
            "- `work/items/" + item["id"] + ".md`",
            "",
            "## Required report",
            "",
            f"Run `python tools/useagent.py task report {item['id']} --agent {agent['id']} --result completed --summary \"...\" --next-action \"Review\"`.",
            "Include changed files, checks/evidence and blockers. The supervisor will review before done.",
            "",
            "## Assignment path",
            "",
            f"`{assignment_path}`",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_init(_: argparse.Namespace) -> int:
    ensure_layout()
    print(f"initialized UseAgent supervisor layout at {ROOT}")
    return 0


def cmd_task_new(args: argparse.Namespace) -> int:
    ensure_layout()
    with state_lock():
        data = load_registry()
        if not args.scope:
            raise UseAgentError("task needs at least one --scope")
        if not args.acceptance:
            raise UseAgentError("task needs at least one --acceptance")
        for dependency in args.depends_on or []:
            if dependency not in data["items"]:
                raise UseAgentError(f"unknown dependency: {dependency}")
        task_id = next_id(data["items"])
        item = {
            "id": task_id,
            "title": args.title,
            "objective": args.objective or args.title,
            "level": args.level,
            "status": "planned",
            "owner": args.owner,
            "assigned_to": None,
            "scope": [normalize_scope(scope) for scope in args.scope],
            "depends_on": args.depends_on or [],
            "preferred_agents": args.preferred_agent or [],
            "capabilities": args.capability or [],
            "acceptance": args.acceptance,
            "verification": args.verification or [],
            "files": [],
            "evidence": [],
            "reports": [],
            "attempts": 0,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        data["items"][task_id] = item
        save_registry(data)
        atomic_write(item_path(task_id), render_item(item))
    print(task_id)
    return 0


def cmd_task_claim(args: argparse.Namespace) -> int:
    with state_lock():
        data = load_registry()
        item = get_item(data, args.task_id)
        if item["status"] not in {"planned", "assigned", "blocked"}:
            raise UseAgentError(f"{args.task_id} is {item['status']}, not claimable")
        if item.get("assigned_to") and item["assigned_to"] != args.agent:
            raise UseAgentError(f"{args.task_id} is assigned to {item['assigned_to']}, not {args.agent}")
        if not dependencies_done(data, item):
            raise UseAgentError(f"{args.task_id} has unfinished dependencies: {item.get('depends_on', [])}")
        conflict = active_scope_conflict(data, item, ignore_id=args.task_id)
        if conflict:
            raise UseAgentError(f"scope conflicts with active task {conflict['id']}: {conflict.get('scope', [])}")
        item["status"] = "in_progress"
        item["assigned_to"] = args.agent
        item["attempts"] = int(item.get("attempts", 0)) + 1
        item["updated_at"] = now_iso()
        save_registry(data)
        sync_item_frontmatter(item)
        append_event(args.task_id, f"claimed by {args.agent}")
    print(f"{args.task_id} claimed by {args.agent}")
    return 0


def cmd_task_update(args: argparse.Namespace) -> int:
    with state_lock():
        data = load_registry()
        item = get_item(data, args.task_id)
        assigned = item.get("assigned_to")
        if args.agent and assigned and args.agent != assigned:
            raise UseAgentError(f"{args.task_id} is assigned to {assigned}, not {args.agent}")
        current = item["status"]
        if args.status == "assigned":
            raise UseAgentError("use supervisor cycle/dispatch to assign a task")
        if args.status == "in_progress" and current not in {"assigned", "in_progress"}:
            raise UseAgentError("use task claim before moving a task into in_progress")
        if args.status == "reported" and current not in {"assigned", "in_progress"}:
            raise UseAgentError("use task report for a worker completion")
        if args.status == "needs_review" and current not in {"reported", "in_progress"}:
            raise UseAgentError("a task must be reported or active before review")
        if args.status == "done" and current not in {"reported", "needs_review", "in_progress"}:
            raise UseAgentError("a task must be active or in review before done")
        if args.status == "done" and not item.get("evidence"):
            raise UseAgentError("a task needs at least one evidence entry before done")
        if args.status in ACTIVE_WRITER_STATUSES and not assigned:
            raise UseAgentError("active task needs an existing assignment; use task claim")
        if args.scopes:
            proposed = dict(item)
            proposed["scope"] = sorted(set(item.get("scope", []) + [normalize_scope(path) for path in args.scopes]))
            conflict = active_scope_conflict(data, proposed, ignore_id=args.task_id)
            if conflict:
                raise UseAgentError(f"scope conflicts with active task {conflict['id']}: {conflict.get('scope', [])}")
            item["scope"] = proposed["scope"]
        if args.status == "planned":
            item["assigned_to"] = None
        item["status"] = args.status
        if args.files:
            item["files"] = sorted(set(item.get("files", []) + [normalize_scope(path) for path in args.files]))
        item["updated_at"] = now_iso()
        save_registry(data)
        sync_item_frontmatter(item)
        append_event(args.task_id, f"status -> {args.status}" + (f": {args.note}" if args.note else ""))
    print(f"{args.task_id}: {args.status}")
    return 0


def parse_evidence(value: str, kind: str | None = None) -> dict[str, str]:
    if kind:
        return {"kind": kind, "value": value}
    if "=" not in value:
        raise UseAgentError("evidence must use --kind <kind> --value <value>")
    parsed_kind, parsed_value = value.split("=", 1)
    if not parsed_kind or not parsed_value:
        raise UseAgentError("evidence kind and value cannot be empty")
    return {"kind": parsed_kind, "value": parsed_value}


def cmd_task_evidence(args: argparse.Namespace) -> int:
    with state_lock():
        data = load_registry()
        item = get_item(data, args.task_id)
        evidence = parse_evidence(args.value, args.kind)
        evidence["recorded_at"] = now_iso()
        item.setdefault("evidence", []).append(evidence)
        item["updated_at"] = now_iso()
        save_registry(data)
        append_event(args.task_id, f"evidence {evidence['kind']}: {evidence['value']}")
    print(f"evidence added to {args.task_id}")
    return 0


def cmd_task_list(args: argparse.Namespace) -> int:
    data = load_registry()
    items = list(data["items"].values())
    if args.status:
        items = [item for item in items if item.get("status") == args.status]
    for item in sorted(items, key=lambda value: value["id"]):
        deps = ",".join(item.get("depends_on", [])) or "-"
        assigned = item.get("assigned_to") or "-"
        print(f"{item['id']}\t{item['status']}\t{item['level']}\t{assigned}\t{item['title']}\tdeps:{deps}")
    return 0


def cmd_task_show(args: argparse.Namespace) -> int:
    data = load_registry()
    print(json.dumps(get_item(data, args.task_id), indent=2, ensure_ascii=False))
    return 0


def cmd_task_report(args: argparse.Namespace) -> int:
    config = load_config()
    with state_lock():
        data = load_registry()
        item = get_item(data, args.task_id)
        if item.get("assigned_to") != args.agent:
            raise UseAgentError(f"{args.task_id} is assigned to {item.get('assigned_to')}, not {args.agent}")
        if item.get("status") not in {"assigned", "in_progress"}:
            raise UseAgentError(f"{args.task_id} is {item.get('status')}, not reportable")
        agent = agent_config(config, args.agent)
        paths = agent_paths(config, agent)
        report_id = f"{args.task_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        report_path = path_for(config, "reports_inbox") / f"{report_id}.md"
        files = [normalize_scope(path) for path in args.files or []]
        checks = args.checks or []
        report_lines = [
            "---",
            "type: useagent-worker-report",
            f"task_id: {item['id']}",
            f"agent: {args.agent}",
            f"result: {args.result}",
            f"created_at: {now_iso()}",
            f"files: {json.dumps(files, ensure_ascii=False)}",
            f"checks: {json.dumps(checks, ensure_ascii=False)}",
            "---",
            "",
            f"# Worker report {item['id']}",
            "",
            "## Summary",
            "",
            args.summary,
            "",
            "## Next action",
            "",
            args.next_action,
            "",
            "## Blockers",
            "",
            args.blocker or "- none",
            "",
            "## Evidence",
            "",
        ]
        report_lines.extend(f"- {check}" for check in checks)
        if not checks:
            report_lines.append("- Add focused evidence before review")
        report_lines.append("")
        atomic_write(report_path, "\n".join(report_lines))

        item.setdefault("reports", []).append(rel(report_path))
        item["files"] = sorted(set(item.get("files", []) + files))
        for check in checks:
            item.setdefault("evidence", []).append({"kind": "check", "value": check, "recorded_at": now_iso()})
        item["status"] = "blocked" if args.result == "blocked" else "reported"
        item["last_result"] = args.result
        item["updated_at"] = now_iso()
        save_registry(data)
        sync_item_frontmatter(item)
        append_event(item["id"], f"worker report {rel(report_path)} result={args.result}")

        write_if_missing(paths["report"], f"# Reports for {args.agent}\n\n")
        append_markdown(paths["report"], f"## {now_iso()} - {item['id']} ({args.result})\n\n{args.summary}\n\n- Report: `{rel(report_path)}`\n- Next: {args.next_action}\n\n")
        if args.result == "completed":
            write_if_missing(paths["completed"], f"# Completed reports for {args.agent}\n\n")
            append_markdown(paths["completed"], f"- {now_iso()} - `{item['id']}` - {item['title']} - pending review - `{rel(report_path)}`\n")
            completed = path_for(config, "completed_tasks")
            write_if_missing(completed, "# Completed task reports\n\n")
            append_markdown(completed, f"- {now_iso()} - `{item['id']}` - {item['title']} - worker completed, pending supervisor/reviewer - `{rel(report_path)}`\n")
        reports_index = path_for(config, "reports_index")
        write_if_missing(reports_index, "# Worker reports\n\n")
        append_markdown(reports_index, f"- {now_iso()} - `{item['id']}` - `{args.agent}` - {args.result} - `{rel(report_path)}`\n")
    print(rel(report_path))
    return 0


def cmd_agent_register(args: argparse.Namespace) -> int:
    ensure_layout()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", args.agent_id):
        raise UseAgentError("agent id must be lowercase and use letters, digits, _ or -")
    with state_lock():
        config = load_config()
        if any(agent.get("id") == args.agent_id for agent in config["agents"]):
            raise UseAgentError(f"agent already registered: {args.agent_id}")
        directory = normalize_scope(args.directory or f"{config['paths']['agent_root']}/{args.agent_id}")
        agent = {
            "id": args.agent_id,
            "role": args.role,
            "status": "available",
            "directory": directory,
            "scope": [normalize_scope(scope) for scope in args.scope or []],
            "capabilities": args.capability or [],
            "max_active": args.max_active,
        }
        if args.inbox_file:
            agent["inbox"] = args.inbox_file
        if args.report_file:
            agent["report"] = args.report_file
        if args.completed_file:
            agent["completed"] = args.completed_file
        paths = agent_paths(config, agent)
        paths["directory"].mkdir(parents=True, exist_ok=True)
        paths["inbox_dir"].mkdir(parents=True, exist_ok=True)
        write_if_missing(paths["inbox"], f"# INBOX - {args.agent_id}\n\n")
        write_if_missing(paths["report"], f"# REPORTS - {args.agent_id}\n\n")
        write_if_missing(paths["completed"], f"# COMPLETED - {args.agent_id}\n\n")
        config["agents"].append(agent)
        save_config(config)
    print(f"registered agent {args.agent_id} at {directory}")
    return 0


def cmd_agent_status(args: argparse.Namespace) -> int:
    with state_lock():
        config = load_config()
        agent = agent_config(config, args.agent_id)
        agent["status"] = args.status
        save_config(config)
    print(f"{args.agent_id}: {args.status}")
    return 0


def cmd_agent_list(_: argparse.Namespace) -> int:
    config = load_config()
    data = load_registry()
    for agent in config.get("agents", []):
        active = sum(1 for item in data["items"].values() if item.get("assigned_to") == agent.get("id") and item.get("status") in ACTIVE_WRITER_STATUSES)
        print(f"{agent['id']}\t{agent.get('status', 'available')}\tactive:{active}/{agent.get('max_active', 1)}\trole:{agent.get('role', 'worker')}")
    return 0


def agent_active_count(data: dict[str, Any], agent_id: str) -> int:
    return sum(1 for item in data["items"].values() if item.get("assigned_to") == agent_id and item.get("status") in ACTIVE_WRITER_STATUSES)


def agent_can_take(config: dict[str, Any], data: dict[str, Any], item: dict[str, Any], agent: dict[str, Any]) -> bool:
    if agent.get("status") != "available":
        return False
    if agent_active_count(data, agent["id"]) >= int(agent.get("max_active", 1)):
        return False
    if agent.get("role") in {"supervisor", "reviewer", "release_gate"}:
        return False
    allowed_scopes = agent.get("scope", [])
    if allowed_scopes and not all(any(scope_within(task_scope, allowed) for allowed in allowed_scopes) for task_scope in item.get("scope", [])):
        return False
    capabilities = set(agent.get("capabilities", []))
    required = set(item.get("capabilities", []))
    return not required or required.issubset(capabilities)


def choose_agent(config: dict[str, Any], data: dict[str, Any], item: dict[str, Any]) -> dict[str, Any] | None:
    agents = config.get("agents", [])
    preferred = item.get("preferred_agents", [])
    ordered = [agent for agent_id in preferred for agent in agents if agent.get("id") == agent_id]
    ordered += [agent for agent in agents if agent.get("id") not in preferred]
    for agent in ordered:
        if agent_can_take(config, data, item, agent):
            return agent
    return None


def assign_task_locked(config: dict[str, Any], data: dict[str, Any], item: dict[str, Any], agent: dict[str, Any]) -> str:
    paths = agent_paths(config, agent)
    assignment_path = paths["inbox_dir"] / f"{item['id']}.md"
    assignment_rel = rel(assignment_path)
    item["status"] = "assigned"
    item["assigned_to"] = agent["id"]
    item["assignment_path"] = assignment_rel
    item["dispatched_at"] = now_iso()
    item["updated_at"] = now_iso()
    content = render_assignment(item, agent, assignment_rel)
    atomic_write(assignment_path, content)
    outbox_path = path_for(config, "outbox") / f"{item['id']}-to-{agent['id']}.md"
    atomic_write(outbox_path, content)
    write_if_missing(paths["inbox"], f"# INBOX - {agent['id']}\n\n")
    append_markdown(paths["inbox"], f"- {now_iso()} - `{item['id']}` assigned - `{assignment_rel}`\n")
    return assignment_rel


def dispatch_ready_locked(config: dict[str, Any], data: dict[str, Any], max_assignments: int, retry_blocked: bool = False) -> list[dict[str, str]]:
    candidates = [
        item
        for item in data["items"].values()
        if item.get("status") == "planned" or (retry_blocked and item.get("status") == "blocked")
    ]
    candidates.sort(key=lambda item: (item.get("level", "L4"), item.get("id", "")))
    assignments: list[dict[str, str]] = []
    for item in candidates:
        if len(assignments) >= max_assignments or not dependencies_done(data, item):
            continue
        conflict = active_scope_conflict(data, item, ignore_id=item["id"])
        if conflict:
            continue
        agent = choose_agent(config, data, item)
        if not agent:
            continue
        assignment_rel = assign_task_locked(config, data, item, agent)
        assignments.append({"task_id": item["id"], "agent": agent["id"], "path": assignment_rel})
    if assignments:
        save_registry(data)
        for assignment in assignments:
            sync_item_frontmatter(get_item(data, assignment["task_id"]))
            append_event(assignment["task_id"], f"dispatched to {assignment['agent']} at {assignment['path']}")
    return assignments


def cmd_supervisor_dispatch(args: argparse.Namespace) -> int:
    ensure_layout()
    config = load_config()
    max_assignments = args.max_assignments or int(config["supervisor"].get("max_assignments_per_cycle", 4))
    with state_lock():
        data = load_registry()
        assignments = dispatch_ready_locked(config, data, max_assignments, retry_blocked=args.retry_blocked) if config["supervisor"].get("auto_dispatch", True) else []
    if assignments:
        for assignment in assignments:
            print(f"{assignment['task_id']} -> {assignment['agent']} ({assignment['path']})")
    else:
        print("no task dispatched")
    return 0


def cmd_worker_pull(args: argparse.Namespace) -> int:
    config = load_config()
    with state_lock():
        data = load_registry()
        agent = agent_config(config, args.agent)
        assigned = [item for item in data["items"].values() if item.get("assigned_to") == args.agent and item.get("status") == "assigned"]
        if not assigned:
            print("NO_TASK")
            return 0
        assigned.sort(key=lambda item: item.get("dispatched_at", item.get("id", "")))
        item = assigned[0]
        item["status"] = "in_progress"
        item["started_at"] = now_iso()
        item["updated_at"] = now_iso()
        save_registry(data)
        sync_item_frontmatter(item)
        append_event(item["id"], f"pulled by {args.agent}")
        path = Path(item["assignment_path"]) if Path(item["assignment_path"]).is_absolute() else ROOT / item["assignment_path"]
    print(path.read_text(encoding="utf-8"))
    return 0


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def parse_frontmatter_json(frontmatter: dict[str, str], key: str, default: Any) -> Any:
    value = frontmatter.get(key)
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip('"')


def load_supervisor_state(config: dict[str, Any]) -> dict[str, Any]:
    path = path_for(config, "supervisor_state")
    if not path.exists():
        return {"version": 1, "cycle": 0, "ingested_reports": [], "last_qa": None}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UseAgentError(f"invalid supervisor state: {exc}") from exc
    return value if isinstance(value, dict) else {"version": 1, "cycle": 0, "ingested_reports": [], "last_qa": None}


def save_supervisor_state(config: dict[str, Any], state: dict[str, Any]) -> None:
    atomic_write(path_for(config, "supervisor_state"), json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def ingest_reports_locked(config: dict[str, Any], data: dict[str, Any], state: dict[str, Any]) -> list[str]:
    inbox = path_for(config, "reports_inbox")
    processed = set(state.get("ingested_reports", []))
    ingested: list[str] = []
    for report_path in sorted(inbox.glob("*.md")):
        if report_path.name.lower() == "readme.md" or rel(report_path) in processed:
            continue
        frontmatter = parse_frontmatter(report_path)
        if frontmatter.get("type") != "useagent-worker-report":
            continue
        task_id = frontmatter.get("task_id")
        if not task_id or task_id not in data["items"]:
            continue
        item = data["items"][task_id]
        report_rel = rel(report_path)
        if report_rel not in item.setdefault("reports", []):
            item["reports"].append(report_rel)
        files = parse_frontmatter_json(frontmatter, "files", [])
        if isinstance(files, list):
            item["files"] = sorted(set(item.get("files", []) + [normalize_scope(str(path)) for path in files]))
        result = frontmatter.get("result")
        if result == "blocked":
            item["status"] = "blocked"
        elif result in {"completed", "failed"} and item.get("status") in {"assigned", "in_progress"}:
            item["status"] = "reported"
        item["updated_at"] = now_iso()
        processed.add(report_rel)
        ingested.append(report_rel)
        append_event(task_id, f"ingested report {report_rel}")
    if ingested:
        save_registry(data)
        state["ingested_reports"] = sorted(processed)
        state["last_ingest_at"] = now_iso()
    return ingested


def cmd_supervisor_ingest(_: argparse.Namespace) -> int:
    config = load_config()
    with state_lock():
        data = load_registry()
        state = load_supervisor_state(config)
        ingested = ingest_reports_locked(config, data, state)
        save_supervisor_state(config, state)
    print("\n".join(ingested) if ingested else "no new reports")
    return 0


def run_qa(config: dict[str, Any], cycle_id: str) -> dict[str, Any]:
    commands = config["supervisor"].get("qa_commands", [])
    if not commands:
        return {"status": "not_configured", "commands": [], "evidence": None}
    timeout = int(config["supervisor"].get("qa_timeout_seconds", 900))
    results = []
    for command in commands:
        started = time.monotonic()
        try:
            result = subprocess.run(
                str(command),
                cwd=ROOT,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            results.append({"command": str(command), "returncode": result.returncode, "duration_sec": round(time.monotonic() - started, 2), "stdout": result.stdout, "stderr": result.stderr})
        except subprocess.TimeoutExpired as exc:
            results.append({"command": str(command), "returncode": 124, "duration_sec": round(time.monotonic() - started, 2), "stdout": str(exc.stdout or ""), "stderr": f"timeout after {timeout}s"})
    status = "pass" if all(result["returncode"] == 0 for result in results) else "fail"
    evidence_path = path_for(config, "evidence") / f"{cycle_id}-qa.md"
    lines = [f"# QA evidence {cycle_id}", ""]
    for result in results:
        lines.extend([f"## `{result['command']}`", "", f"- returncode: `{result['returncode']}`", f"- duration_sec: `{result['duration_sec']}`", "", "### stdout", "", "```text", result["stdout"], "```", "", "### stderr", "", "```text", result["stderr"], "```", ""])
    atomic_write(evidence_path, "\n".join(lines))
    return {"status": status, "commands": results, "evidence": rel(evidence_path)}


def production_snapshot(config: dict[str, Any], data: dict[str, Any], state: dict[str, Any]) -> tuple[list[tuple[str, str]], bool]:
    items = list(data["items"].values())
    if not items:
        task_gate = "manual"
    else:
        task_gate = "pass" if all(item.get("status") in {"done", "cancelled"} for item in items) else "fail"
    qa_status = (state.get("last_qa") or {}).get("status", "not_configured")
    qa_gate = "pass" if qa_status == "pass" else "manual" if qa_status == "not_configured" else "fail"
    blocked_gate = "pass" if not any(item.get("status") == "blocked" for item in items) else "fail"
    readiness_files = config["supervisor"].get("operational_readiness_files", [])
    readiness_gate = "manual"
    try:
        if isinstance(readiness_files, list) and readiness_files:
            readiness_gate = "pass"
            for value in readiness_files:
                candidate = safe_repo_path(value)
                if not candidate.is_file() or not candidate.read_text(encoding="utf-8").strip():
                    readiness_gate = "manual"
                    break
    except (OSError, TypeError, UseAgentError):
        readiness_gate = "manual"
    gates = [
        ("all_tasks_done", task_gate),
        ("qa", qa_gate),
        ("no_blocked_tasks", blocked_gate),
        ("operational_rollback_notes", readiness_gate),
    ]
    return gates, all(value == "pass" for _, value in gates)


def choose_next_action(data: dict[str, Any], assignments: list[dict[str, str]], config: dict[str, Any], qa_result: dict[str, Any] | None = None) -> str:
    blocked = [item for item in data["items"].values() if item.get("status") == "blocked"]
    failed = [item for item in data["items"].values() if item.get("last_result") == "failed"]
    reported = [item for item in data["items"].values() if item.get("status") == "reported"]
    planned = [item for item in data["items"].values() if item.get("status") == "planned" and dependencies_done(data, item)]
    active = [item for item in data["items"].values() if item.get("status") in ACTIVE_WRITER_STATUSES]
    if blocked:
        return f"Resolve blocker for {blocked[0]['id']} and attach the missing decision/evidence."
    if qa_result and qa_result.get("status") == "fail":
        return f"Read QA evidence at {qa_result.get('evidence')}; create a scoped debug task before dispatching more work."
    if failed:
        return f"Read the failed worker report for {failed[0]['id']} and create a scoped debug task with a new hypothesis."
    if reported:
        return f"Review worker report for {reported[0]['id']}; run QA and create a debug task if evidence fails."
    if assignments:
        return f"Workers pull assigned tasks from their INBOX.md; wait for reports from {', '.join(a['task_id'] for a in assignments)}."
    if planned:
        return "Register an eligible worker or widen its configured scope/capabilities, then dispatch again."
    if active:
        return "Wait for active workers to report; do not assign overlapping writers."
    if data["items"] and all(item.get("status") in {"done", "cancelled"} for item in data["items"].values()):
        return "Run the production release gate and obtain explicit deploy approval."
    return "Create the next scoped work item from the project goal."


def build_supervisor_report(config: dict[str, Any], data: dict[str, Any], state: dict[str, Any], cycle_id: str, ingested: list[str], assignments: list[dict[str, str]], qa_result: dict[str, Any]) -> tuple[str, str]:
    counts: dict[str, int] = {}
    for item in data["items"].values():
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    next_action = choose_next_action(data, assignments, config, qa_result)
    gates, production_ready = production_snapshot(config, data, state)
    lines = [
        "# UseAgent supervisor report",
        "",
        f"- **Cycle:** `{cycle_id}`",
        f"- **Generated:** {now_iso()}",
        f"- **Next action:** {next_action}",
        f"- **Production snapshot:** `{'ready' if production_ready else 'not_ready'}`",
        "",
        "## Status counts",
        "",
    ]
    lines.extend(f"- `{status}`: {count}" for status, count in sorted(counts.items()))
    lines.extend(["", "## Reports ingested this cycle", ""])
    lines.extend(f"- `{path}`" for path in ingested) or lines.append("- none")
    lines.extend(["", "## Assignments issued this cycle", ""])
    lines.extend(f"- `{entry['task_id']}` -> `{entry['agent']}` — `{entry['path']}`" for entry in assignments) or lines.append("- none")
    lines.extend(["", "## Worker reports awaiting review", ""])
    awaiting = [item for item in data["items"].values() if item.get("status") in {"reported", "needs_review"}]
    lines.extend(f"- `{item['id']}` — {item['title']} — reports: {', '.join(item.get('reports', [])) or 'none'}" for item in awaiting) or lines.append("- none")
    lines.extend(["", "## Completed tasks", ""])
    completed = [item for item in data["items"].values() if item.get("status") == "done"]
    lines.extend(f"- `{item['id']}` — {item['title']} — evidence: {len(item.get('evidence', []))}" for item in completed) or lines.append("- none")
    lines.extend(["", "## Blocked work", ""])
    blocked = [item for item in data["items"].values() if item.get("status") == "blocked"]
    lines.extend(f"- `{item['id']}` — {item['title']}" for item in blocked) or lines.append("- none")
    lines.extend(["", "## QA", "", f"- status: `{qa_result.get('status')}`", f"- evidence: `{qa_result.get('evidence') or 'none'}`", ""])
    lines.extend(["## Production gates", ""])
    for name, value in gates:
        lines.append(f"- [{'x' if value == 'pass' else ' '}] `{name}`: `{value}`")
    lines.extend(["", "## Resume instruction", "", f"{next_action}", ""])
    return "\n".join(lines), next_action


def write_checkpoint(config: dict[str, Any], name: str, status: str, summary: str, next_action: str, tasks: list[str], blockers: list[str], agent: str) -> Path:
    checkpoint_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'cycle'}"
    path = path_for(config, "checkpoints") / f"{checkpoint_id}.md"
    lines = [
        f"# Checkpoint: {name}",
        "",
        f"- **Created:** {now_iso()}",
        f"- **Status:** {status}",
        f"- **Agent:** {agent}",
        f"- **Next action:** {next_action}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Tasks",
        "",
    ]
    lines.extend(f"- `{task}`" for task in tasks) or lines.append("- none")
    lines.extend(["", "## Blockers and risks", ""])
    lines.extend(f"- {blocker}" for blocker in blockers) or lines.append("- none")
    lines.extend(["", "## Resume instructions", "", next_action, ""])
    atomic_write(path, "\n".join(lines))
    return path


def cmd_checkpoint_create(args: argparse.Namespace) -> int:
    config = load_config()
    with state_lock():
        ensure_layout()
        path = write_checkpoint(config, args.name, args.status, args.summary, args.next_action, args.tasks or [], args.blockers or [], args.agent)
        state = load_supervisor_state(config)
        state["last_checkpoint"] = rel(path)
        save_supervisor_state(config, state)
    print(rel(path))
    return 0


def cmd_supervisor_report(args: argparse.Namespace) -> int:
    config = load_config()
    with state_lock():
        data = load_registry()
        state = load_supervisor_state(config)
        cycle_id = f"manual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        report, _ = build_supervisor_report(config, data, state, cycle_id, [], [], state.get("last_qa") or {"status": "not_configured"})
        atomic_write(path_for(config, "supervisor_report"), report)
        atomic_write(path_for(config, "supervisor_cycle"), report)
    print(rel(path_for(config, "supervisor_report")))
    return 0


def cmd_supervisor_qa(_: argparse.Namespace) -> int:
    config = load_config()
    cycle_id = f"manual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    result = run_qa(config, cycle_id)
    with state_lock():
        state = load_supervisor_state(config)
        state["last_qa"] = result
        state["last_qa_at"] = now_iso()
        save_supervisor_state(config, state)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"pass", "not_configured"} else 1


def cmd_supervisor_cycle(args: argparse.Namespace) -> int:
    ensure_layout()
    config = load_config()
    cycle_id = f"cycle-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    with state_lock():
        data = load_registry()
        state = load_supervisor_state(config)
        ingested = ingest_reports_locked(config, data, state)
        max_assignments = args.max_assignments or int(config["supervisor"].get("max_assignments_per_cycle", 4))
        assignments = dispatch_ready_locked(config, data, max_assignments, retry_blocked=args.retry_blocked)
        state["cycle"] = int(state.get("cycle", 0)) + 1
        state["last_cycle_id"] = cycle_id
        save_supervisor_state(config, state)
    should_run_qa = args.run_qa or bool(config["supervisor"].get("run_qa_each_cycle"))
    qa_result = run_qa(config, cycle_id) if should_run_qa else (load_supervisor_state(config).get("last_qa") or {"status": "not_run", "evidence": None})
    with state_lock():
        data = load_registry()
        state = load_supervisor_state(config)
        state["last_qa"] = qa_result
        state["last_qa_at"] = now_iso()
        report, next_action = build_supervisor_report(config, data, state, cycle_id, ingested, assignments, qa_result)
        atomic_write(path_for(config, "supervisor_report"), report)
        atomic_write(path_for(config, "supervisor_cycle"), report)
        save_supervisor_state(config, state)
        checkpoint_status = "needs_input" if any(item.get("status") == "blocked" for item in data["items"].values()) else "active"
        checkpoint = write_checkpoint(config, cycle_id, checkpoint_status, f"Ingested {len(ingested)} reports, issued {len(assignments)} assignments, QA={qa_result.get('status')}.", next_action, [item["id"] for item in data["items"].values() if item.get("status") not in {"done", "cancelled"}], [item["id"] for item in data["items"].values() if item.get("status") == "blocked"], "supervisor")
        state["last_checkpoint"] = rel(checkpoint)
        save_supervisor_state(config, state)
    print(f"cycle={cycle_id}")
    print(f"report={rel(path_for(config, 'supervisor_report'))}")
    print(f"checkpoint={rel(checkpoint)}")
    print(f"next={next_action}")
    return 0


def parse_frontmatter_for_skill(path: Path) -> dict[str, str]:
    return parse_frontmatter(path)


def validate_registry(data: dict[str, Any], errors: list[str]) -> None:
    items = data.get("items")
    if not isinstance(items, dict):
        errors.append("registry.items must be an object")
        return
    for task_id, item in items.items():
        if not re.fullmatch(r"UA-\d{4,}", task_id):
            errors.append(f"invalid task id: {task_id}")
        if not isinstance(item, dict):
            errors.append(f"{task_id} must be an object")
            continue
        for field in ("title", "level", "status", "owner", "scope", "depends_on", "acceptance", "evidence", "reports"):
            if field not in item:
                errors.append(f"{task_id} missing {field}")
        if item.get("level") not in VALID_LEVELS:
            errors.append(f"{task_id} has invalid level {item.get('level')}")
        if item.get("status") not in VALID_STATUSES:
            errors.append(f"{task_id} has invalid status {item.get('status')}")
        if not isinstance(item.get("scope"), list) or not item.get("scope"):
            errors.append(f"{task_id} needs a non-empty scope")
        if not isinstance(item.get("acceptance"), list) or not item.get("acceptance"):
            errors.append(f"{task_id} needs acceptance criteria")
        for dependency in item.get("depends_on", []):
            if dependency not in items:
                errors.append(f"{task_id} references missing dependency {dependency}")
        if item.get("status") == "done" and not item.get("evidence"):
            errors.append(f"{task_id} is done without evidence")
        if item.get("status") == "assigned" and not item.get("assigned_to"):
            errors.append(f"{task_id} is assigned without assigned_to")
        if item.get("status") == "reported" and not item.get("reports"):
            errors.append(f"{task_id} is reported without a report path")
        if not item_path(task_id).exists():
            errors.append(f"missing work item file: {rel(item_path(task_id))}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"dependency cycle includes {task_id}")
            return
        if task_id in visited or task_id not in items:
            return
        visiting.add(task_id)
        for dependency in items[task_id].get("depends_on", []):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in items:
        visit(task_id)

    active = [(task_id, item) for task_id, item in items.items() if item.get("status") in ACTIVE_WRITER_STATUSES]
    for index, (left_id, left) in enumerate(active):
        for right_id, right in active[index + 1 :]:
            if any(scope_overlaps(a, b) for a in left.get("scope", []) for b in right.get("scope", [])):
                errors.append(f"active writer scope conflict: {left_id} vs {right_id}")


def validate_config(config: dict[str, Any], errors: list[str]) -> None:
    seen: set[str] = set()
    for agent in config.get("agents", []):
        agent_id = agent.get("id")
        if not agent_id or agent_id in seen:
            errors.append(f"invalid or duplicate agent id: {agent_id}")
        seen.add(agent_id)
        if agent.get("status", "available") not in VALID_AGENT_STATUSES:
            errors.append(f"invalid status for agent {agent_id}")
        try:
            paths = agent_paths(config, agent)
        except UseAgentError as exc:
            errors.append(str(exc))
            continue
        for key in ("inbox", "report", "completed", "inbox_dir"):
            if not paths[key].exists():
                errors.append(f"missing mailbox file/dir for {agent_id}: {rel(paths[key])}")


def cmd_validate(_: argparse.Namespace) -> int:
    errors: list[str] = []
    required_files = [
        ROOT / "AGENTS.md",
        ROOT / "knowledge" / "INDEX.md",
        ROOT / "knowledge" / "project-map.md",
        ROOT / "work" / "INDEX.md",
        ROOT / "work" / "registry.json",
        ROOT / "useagent.config.json",
        ROOT / "tools" / "useagent.py",
    ]
    for path in required_files:
        if not path.exists():
            errors.append(f"missing required file: {rel(path)}")
    config: dict[str, Any] = {}
    if CONFIG.exists():
        try:
            config = load_config()
            validate_config(config, errors)
        except UseAgentError as exc:
            errors.append(str(exc))
    if REGISTRY.exists():
        try:
            validate_registry(load_registry(), errors)
        except UseAgentError as exc:
            errors.append(str(exc))

    expected_skills = {"useagent", "useagent-orchestrator", "useagent-context", "useagent-worker", "useagent-review", "useagent-autopilot"}
    skills_root = ROOT / ".agents" / "skills"
    for skill_name in expected_skills:
        skill_dir = skills_root / skill_name
        path = skill_dir / "SKILL.md"
        if not path.exists():
            errors.append(f"missing skill: {rel(path)}")
            continue
        frontmatter = parse_frontmatter_for_skill(path)
        if frontmatter.get("name") != skill_name:
            errors.append(f"skill name mismatch in {rel(path)}")
        if not frontmatter.get("description") or "TODO" in frontmatter.get("description", ""):
            errors.append(f"skill description missing or unfinished in {rel(path)}")
        if "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"unfinished TODO in {rel(path)}")

    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None
    for path in sorted((ROOT / ".codex" / "agents").glob("*.toml")):
        if tomllib is None:
            errors.append("Python 3.11+ is required to validate TOML custom agents")
            break
        try:
            agent = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid TOML {rel(path)}: {exc}")
            continue
        for field in ("name", "description", "developer_instructions"):
            if not agent.get(field):
                errors.append(f"custom agent {rel(path)} missing {field}")

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    config = load_config()
    data = load_registry()
    sections = []
    for path in (ROOT / "knowledge" / "INDEX.md", ROOT / "knowledge" / "project-brief.md", ROOT / "knowledge" / "project-map.md", path_for(config, "supervisor_report")):
        if path.exists():
            sections.append(f"## {rel(path)}\n{path.read_text(encoding='utf-8')}")
    active = [item for item in data["items"].values() if item.get("status") not in {"done", "cancelled"}]
    summary = [f"- {item['id']} [{item['status']}] {item['level']}: {item['title']} | scope={','.join(item.get('scope', []))}" for item in sorted(active, key=lambda value: value["id"])]
    sections.append("## active work\n" + ("\n".join(summary) if summary else "(none)"))
    if args.task_id:
        item = get_item(data, args.task_id)
        path = item_path(args.task_id)
        body = path.read_text(encoding="utf-8") if path.exists() else json.dumps(item, indent=2)
        sections.append(f"## task {args.task_id}\n{body}")
    print(clip("\n\n".join(sections), args.max_chars))
    return 0


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 80)] + "\n...[context clipped]...\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="useagent", description="UseAgent supervisor control plane")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create missing runtime directories and config")
    init.set_defaults(func=cmd_init)

    context = sub.add_parser("context", help="print bounded supervisor context")
    context.add_argument("--task", dest="task_id")
    context.add_argument("--max-chars", type=int, default=8000)
    context.set_defaults(func=cmd_context)

    validate = sub.add_parser("validate", help="validate project, skills, roster and registry")
    validate.set_defaults(func=cmd_validate)

    task = sub.add_parser("task", help="manage work items")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_new = task_sub.add_parser("new", help="create planned task")
    task_new.add_argument("--title", required=True)
    task_new.add_argument("--objective")
    task_new.add_argument("--level", required=True, choices=sorted(VALID_LEVELS))
    task_new.add_argument("--owner", required=True)
    task_new.add_argument("--scope", action="append", required=True)
    task_new.add_argument("--acceptance", action="append", required=True)
    task_new.add_argument("--verification", action="append")
    task_new.add_argument("--preferred-agent", action="append")
    task_new.add_argument("--capability", action="append")
    task_new.add_argument("--depends-on", nargs="*", default=[])
    task_new.set_defaults(func=cmd_task_new)

    claim = task_sub.add_parser("claim", help="claim a task directly")
    claim.add_argument("task_id")
    claim.add_argument("--agent", required=True)
    claim.set_defaults(func=cmd_task_claim)

    update = task_sub.add_parser("update", help="change task status")
    update.add_argument("task_id")
    update.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    update.add_argument("--agent")
    update.add_argument("--scope", dest="scopes", action="append")
    update.add_argument("--file", dest="files", action="append")
    update.add_argument("--note")
    update.set_defaults(func=cmd_task_update)

    evidence = task_sub.add_parser("evidence", help="append evidence")
    evidence.add_argument("task_id")
    evidence.add_argument("--kind", required=True)
    evidence.add_argument("--value", required=True)
    evidence.set_defaults(func=cmd_task_evidence)

    report = task_sub.add_parser("report", help="write worker report and completed logs")
    report.add_argument("task_id")
    report.add_argument("--agent", required=True)
    report.add_argument("--result", choices=["completed", "blocked", "failed"], required=True)
    report.add_argument("--summary", required=True)
    report.add_argument("--next-action", required=True)
    report.add_argument("--file", dest="files", action="append")
    report.add_argument("--check", dest="checks", action="append")
    report.add_argument("--blocker")
    report.set_defaults(func=cmd_task_report)

    task_list = task_sub.add_parser("list", help="list tasks")
    task_list.add_argument("--status", choices=sorted(VALID_STATUSES))
    task_list.set_defaults(func=cmd_task_list)

    show = task_sub.add_parser("show", help="show task JSON")
    show.add_argument("task_id")
    show.set_defaults(func=cmd_task_show)

    agent = sub.add_parser("agent", help="manage worker roster and mailboxes")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    register = agent_sub.add_parser("register", help="register worker and create mailbox")
    register.add_argument("--id", dest="agent_id", required=True)
    register.add_argument("--role", default="worker")
    register.add_argument("--directory")
    register.add_argument("--inbox-file")
    register.add_argument("--report-file")
    register.add_argument("--completed-file")
    register.add_argument("--scope", action="append")
    register.add_argument("--capability", action="append")
    register.add_argument("--max-active", type=int, default=1)
    register.set_defaults(func=cmd_agent_register)
    agent_status_parser = agent_sub.add_parser("status", help="set worker availability")
    agent_status_parser.add_argument("agent_id")
    agent_status_parser.add_argument("--status", required=True, choices=sorted(VALID_AGENT_STATUSES))
    agent_status_parser.set_defaults(func=cmd_agent_status)
    agent_list = agent_sub.add_parser("list", help="list registered workers")
    agent_list.set_defaults(func=cmd_agent_list)

    worker = sub.add_parser("worker", help="worker mailbox operations")
    worker_sub = worker.add_subparsers(dest="worker_command", required=True)
    pull = worker_sub.add_parser("pull", help="pull oldest assigned task")
    pull.add_argument("--agent", required=True)
    pull.set_defaults(func=cmd_worker_pull)

    supervisor = sub.add_parser("supervisor", help="supervisor dispatch/report/QA cycle")
    supervisor_sub = supervisor.add_subparsers(dest="supervisor_command", required=True)
    dispatch = supervisor_sub.add_parser("dispatch", help="assign ready tasks to eligible workers")
    dispatch.add_argument("--max-assignments", type=int)
    dispatch.add_argument("--retry-blocked", action="store_true")
    dispatch.set_defaults(func=cmd_supervisor_dispatch)
    ingest = supervisor_sub.add_parser("ingest", help="ingest incoming worker reports")
    ingest.set_defaults(func=cmd_supervisor_ingest)
    supervisor_report = supervisor_sub.add_parser("report", help="regenerate user-facing report")
    supervisor_report.set_defaults(func=cmd_supervisor_report)
    qa = supervisor_sub.add_parser("qa", help="run configured QA commands")
    qa.set_defaults(func=cmd_supervisor_qa)
    cycle = supervisor_sub.add_parser("cycle", help="run one bounded supervisor cycle")
    cycle.add_argument("--max-assignments", type=int)
    cycle.add_argument("--retry-blocked", action="store_true")
    cycle.add_argument("--run-qa", action="store_true")
    cycle.set_defaults(func=cmd_supervisor_cycle)

    checkpoint = sub.add_parser("checkpoint", help="create resume checkpoint")
    checkpoint_sub = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    checkpoint_create = checkpoint_sub.add_parser("create", help="create checkpoint")
    checkpoint_create.add_argument("--name", required=True)
    checkpoint_create.add_argument("--status", required=True, choices=["active", "blocked", "complete", "needs_input"])
    checkpoint_create.add_argument("--summary", required=True)
    checkpoint_create.add_argument("--next-action", required=True)
    checkpoint_create.add_argument("--agent", default="supervisor")
    checkpoint_create.add_argument("--task", dest="tasks", action="append")
    checkpoint_create.add_argument("--blocker", dest="blockers", action="append")
    checkpoint_create.set_defaults(func=cmd_checkpoint_create)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except UseAgentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
