from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import relwit.cli as relwit


class UsageTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_root = relwit.ROOT
        self.original_registry = relwit.REGISTRY
        self.original_config = relwit.CONFIG
        self.original_lock = relwit.LOCK
        relwit.ROOT = Path(self.temp_dir.name)
        relwit.REGISTRY = relwit.ROOT / "work" / "registry.json"
        relwit.CONFIG = relwit.ROOT / "relwit.config.json"
        relwit.LOCK = relwit.ROOT / "work" / ".state.lock"
        relwit.ensure_layout()

    def tearDown(self) -> None:
        relwit.ROOT = self.original_root
        relwit.REGISTRY = self.original_registry
        relwit.CONFIG = self.original_config
        relwit.LOCK = self.original_lock
        self.temp_dir.cleanup()

    def event(self, event_id: str, agent: str, start: str, end: str, **extra: object) -> dict[str, object]:
        value: dict[str, object] = {
            "event_id": event_id,
            "schema_version": 1,
            "kind": "task",
            "task_id": event_id,
            "agent_id": agent,
            "role": "worker",
            "attempt": 1,
            "outcome": "completed",
            "started_at": start,
            "completed_at": end,
            "duration_ms": 1000,
            "execution_duration_ms": 1000,
            "usage": relwit.unavailable_usage("missing", "adapter"),
        }
        value.update(extra)
        return value

    def test_measured_wall_duration_is_recorded(self) -> None:
        item = {"id": "UA-0100", "attempts": 1, "started_at": "2026-09-07T00:00:00Z"}
        agent = {"id": "worker-a", "role": "worker"}
        with relwit.state_lock():
            relwit.record_task_telemetry_locked(
                relwit.load_config(), item, agent, "completed", completed_at="2026-09-07T00:00:01.250Z"
            )
        stored = relwit.load_telemetry(relwit.load_config())["events"]
        event = stored["task:UA-0100:attempt:1"]
        self.assertEqual(event["duration_ms"], 1250)
        self.assertEqual(event["duration_provenance"], "measured")

    def test_parallel_workers_wall_time_is_not_sum_of_runtime(self) -> None:
        events = [
            self.event("UA-0101", "worker-a", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z"),
            self.event("UA-0102", "worker-b", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z"),
        ]
        summary = relwit.aggregate_telemetry(events)
        self.assertEqual(summary["wall_time_ms"], 1000)
        self.assertEqual(summary["worker_runtime_ms"], 2000)

    def test_authoritative_adapter_usage_is_accepted(self) -> None:
        usage = relwit.normalize_usage_envelope(
            {
                "relwit_usage": 1,
                "authoritative": True,
                "provider": "openai",
                "runtime": "codex",
                "model": "gpt-5.6-luna",
                "input_tokens": 100,
                "cached_input_tokens": 20,
                "output_tokens": 40,
                "total_tokens": 140,
            }
        )
        self.assertEqual(usage["provenance"], "authoritative")
        self.assertEqual(usage["total_tokens"], 140)

    def test_plain_prose_and_ambiguous_total_are_not_authoritative(self) -> None:
        self.assertEqual(relwit.usage_from_runtime_streams("I used 100 tokens")["provenance"], "unavailable")
        invalid = relwit.normalize_usage_envelope(
            {"relwit_usage": 1, "authoritative": True, "input_tokens": 100, "output_tokens": 40, "total_tokens": 999}
        )
        self.assertEqual(invalid["provenance"], "unavailable")

    def test_missing_usage_is_unavailable_not_zero(self) -> None:
        usage = relwit.normalize_usage_envelope(None)
        self.assertEqual(usage["provenance"], "unavailable")
        self.assertNotIn("total_tokens", usage)

    def test_partial_usage_is_marked_partial(self) -> None:
        events = [
            self.event(
                "UA-0103",
                "worker-a",
                "2026-09-07T00:00:00Z",
                "2026-09-07T00:00:01Z",
                usage={"status": "available", "provenance": "authoritative", "total_tokens": 100},
            ),
            self.event("UA-0104", "worker-b", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z"),
        ]
        summary = relwit.aggregate_telemetry(events)
        self.assertEqual(summary["token_status"], "partial")
        self.assertEqual(summary["tokens"], 100)

    def test_duplicate_event_identity_is_idempotent(self) -> None:
        config = relwit.load_config()
        fields = self.event(
            "UA-0105", "worker-a", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z",
            usage={"status": "available", "provenance": "authoritative", "total_tokens": 55},
        )
        with relwit.state_lock():
            relwit.upsert_telemetry_event_locked(config, "task:UA-0105:attempt:1", fields)
            relwit.upsert_telemetry_event_locked(config, "task:UA-0105:attempt:1", fields)
        summary = relwit.load_telemetry_summary(config)
        self.assertEqual(summary["tokens"], 55)
        self.assertEqual(len(relwit.load_telemetry(config)["events"]), 1)

    def test_retry_keeps_attempts_and_aggregates_usage(self) -> None:
        first = self.event(
            "UA-0106", "worker-a", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z",
            usage={"status": "available", "provenance": "authoritative", "total_tokens": 10},
        )
        second = self.event(
            "UA-0106-retry", "worker-a", "2026-09-07T00:00:02Z", "2026-09-07T00:00:03Z",
            attempt=2, retry=True,
            usage={"status": "available", "provenance": "authoritative", "total_tokens": 20},
        )
        summary = relwit.aggregate_telemetry([first, second])
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["retries"], 1)
        self.assertEqual(summary["tokens"], 30)

    def test_takeover_lineage_is_preserved(self) -> None:
        event = self.event(
            "UA-0107", "worker-recovery", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z",
            takeover=True, supersedes="UA-0009",
        )
        summary = relwit.aggregate_telemetry([event])
        self.assertEqual(summary["takeovers"], 1)
        self.assertEqual(event["supersedes"], "UA-0009")

    def test_participants_are_derived_from_all_event_history(self) -> None:
        events = [
            {"event_id": "assignment:1", "kind": "task", "agent_id": "worker-a", "role": "worker", "task_id": "UA-1"},
            self.event("UA-0108", "worker-b", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z"),
            {"event_id": "review:1", "kind": "task", "agent_id": "reviewer", "role": "reviewer", "task_id": "UA-0108"},
        ]
        participants = relwit.aggregate_telemetry(events)["participants"]
        self.assertEqual(set(participants), {"worker-a", "worker-b", "reviewer"})

    def test_optional_metadata_is_safe_and_provider_neutral(self) -> None:
        usage = relwit.normalize_usage_envelope(
            {
                "relwit_usage": 1,
                "provenance": "measured",
                "input_tokens": 2,
                "output_tokens": 3,
                "provider": "provider-x",
                "runtime": "runtime-y",
                "model": "model-z",
                "account_id": "must-not-be-stored",
                "prompt": "secret prompt",
            },
            source="adapter",
        )
        self.assertEqual(usage["provider"], "provider-x")
        self.assertNotIn("account_id", usage)
        self.assertNotIn("prompt", usage)

    def test_telemetry_store_does_not_persist_raw_prompt_or_secret(self) -> None:
        config = relwit.load_config()
        payload = {
            "relwit_usage": 1,
            "authoritative": True,
            "total_tokens": 7,
            "prompt": "TOP-SECRET-PROMPT",
            "authorization": "Bearer TOP-SECRET-TOKEN",
        }
        usage = relwit.normalize_usage_envelope(payload)
        with relwit.state_lock():
            relwit.upsert_telemetry_event_locked(
                config,
                "cycle:privacy",
                {
                    "kind": "cycle",
                    "entity_id": "privacy",
                    "usage": usage,
                    "prompt": "TOP-SECRET-PROMPT",
                    "raw_log": "TOP-SECRET-LOG",
                },
            )
        content = relwit.telemetry_store_path(config).read_text(encoding="utf-8")
        self.assertNotIn("TOP-SECRET", content)
        self.assertNotIn("authorization", content)

    def test_telemetry_write_does_not_change_source_fingerprint(self) -> None:
        config = relwit.load_config()
        before = relwit.release_source_fingerprint(config)["fingerprint"]
        with relwit.state_lock():
            relwit.upsert_telemetry_event_locked(config, "cycle:fingerprint", {"kind": "cycle", "entity_id": "fingerprint"})
        after = relwit.release_source_fingerprint(config)["fingerprint"]
        self.assertEqual(before, after)

    def test_runtime_failure_classification_remains_provider_neutral(self) -> None:
        result = relwit.classify_runner_failure(1, "provider says quota", "")
        self.assertEqual(result["failure_class"], "runtime_error")
        self.assertFalse(result["authoritative"])

    def test_report_usage_section_is_concise_and_deterministic(self) -> None:
        summary = relwit.aggregate_telemetry(
            [self.event("UA-0109", "worker-b", "2026-09-07T00:00:00Z", "2026-09-07T00:00:01Z")]
        )
        first = relwit.render_usage_section(summary)
        second = relwit.render_usage_section(summary)
        self.assertEqual(first, second)
        self.assertIn("## Usage", first)
        self.assertLess(len("\n".join(first)), 1400)
        self.assertNotIn("events.json", "\n".join(first))

    def test_supervisor_report_includes_usage_without_raw_store(self) -> None:
        config = relwit.load_config()
        with relwit.state_lock():
            relwit.upsert_telemetry_event_locked(
                config,
                "cycle:report",
                {
                    "kind": "cycle",
                    "entity_id": "report",
                    "agent_id": "supervisor",
                    "role": "supervisor",
                    "started_at": "2026-09-07T00:00:00Z",
                    "completed_at": "2026-09-07T00:00:01Z",
                    "duration_ms": 1000,
                    "usage": relwit.unavailable_usage("missing", "supervisor-runtime"),
                },
            )
        data = relwit.load_registry()
        state = relwit.load_supervisor_state(config)
        report, _ = relwit.build_supervisor_report(config, data, state, "report", [], [], {"status": "not_run"})
        self.assertIn("## Usage", report)
        self.assertIn("supervisor (0 tasks)", report)
        self.assertNotIn("TOP-SECRET", report)

    def test_cli_record_accepts_explicit_envelope_without_dumping_it(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = relwit.main(
                [
                    "telemetry", "record", "--kind", "task", "--id", "UA-0110", "--agent", "worker-a",
                    "--event-id", "task:UA-0110:attempt:1", "--outcome", "completed",
                    "--usage-json", json.dumps({"relwit_usage": 1, "authoritative": True, "total_tokens": 9}),
                ]
            )
        self.assertEqual(code, 0)
        self.assertIn("usage=authoritative", stdout.getvalue())
        self.assertNotIn("9", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
