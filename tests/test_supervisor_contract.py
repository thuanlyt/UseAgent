from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPOSITORY_ROOT / "knowledge" / "contracts" / "supervisor-judgment.md"
FRONT_DOOR = REPOSITORY_ROOT / ".agents" / "skills" / "relwit" / "SKILL.md"
SUPERVISOR_REFERENCE = (
    REPOSITORY_ROOT / ".agents" / "skills" / "relwit" / "references" / "supervisor-contract.md"
)
ORCHESTRATOR = REPOSITORY_ROOT / ".agents" / "skills" / "relwit-orchestrator" / "SKILL.md"
AUTOPILOT = REPOSITORY_ROOT / ".agents" / "skills" / "relwit-autopilot" / "SKILL.md"
REVIEW = REPOSITORY_ROOT / ".agents" / "skills" / "relwit-review" / "SKILL.md"
PROTOCOL = REPOSITORY_ROOT / "knowledge" / "contracts" / "supervisor-protocol.md"
README_EN = REPOSITORY_ROOT / "README.md"
README_VI = REPOSITORY_ROOT / "README-vi.md"


def markdown_table_rows(text: str, prefix: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if line.startswith(f"| {prefix}"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


class SupervisorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = CONTRACT.read_text(encoding="utf-8")

    def test_canonical_contract_has_progressive_disclosure_sections(self) -> None:
        headings = {
            line.removeprefix("## ").strip()
            for line in self.contract.splitlines()
            if line.startswith("## ")
        }
        self.assertTrue(
            {
                "Purpose and scope",
                "Intent model",
                "Judgment loop",
                "Autonomy and escalation ladder",
                "Recommendation and owner communication",
                "Claims, audits and uncertainty",
                "Resource and stop discipline",
                "Decision record shape",
                "Deterministic conformance scenarios",
                "Authorization boundary",
            }.issubset(headings)
        )

    def test_intent_and_autonomy_are_structured_contracts(self) -> None:
        intent_rows = markdown_table_rows(self.contract, "Outcome")
        self.assertEqual(len(intent_rows), 1)
        all_rows = markdown_table_rows(self.contract, "")
        intent_kinds = {row[0] for row in all_rows if len(row) >= 3}
        self.assertTrue(
            {
                "Outcome",
                "Constraint",
                "Preference",
                "Proposed solution",
                "Explicit owner decision",
            }.issubset(intent_kinds)
        )
        ladder_section = self.contract.split("## Autonomy and escalation ladder", 1)[1].split(
            "## Recommendation", 1
        )[0]
        self.assertGreaterEqual(ladder_section.count("|"), 12)
        for marker in ("Decide and proceed", "ask one focused question", "Ask the owner", "Recommend stop"):
            self.assertIn(marker, ladder_section)

    def test_decision_record_preserves_reasoning_without_raw_transcript(self) -> None:
        record_section = self.contract.split("## Decision record shape", 1)[1].split(
            "## Deterministic", 1
        )[0]
        required_fields = (
            "Decision:",
            "Outcome:",
            "Constraints:",
            "Options considered:",
            "Recommendation:",
            "Tradeoff/risk:",
            "Confidence:",
            "Owner decision or override:",
            "Evidence/source anchors:",
            "Next action or stop condition:",
        )
        self.assertTrue(all(field in record_section for field in required_fields))
        self.assertNotIn("full chain of thought", record_section.lower())
        self.assertNotIn("raw transcript", record_section.lower())

    def test_twelve_conformance_scenarios_are_structured(self) -> None:
        rows = markdown_table_rows(self.contract, "J")
        ids = [row[0] for row in rows]
        self.assertEqual(ids, [f"J{index:02d}" for index in range(1, 13)])
        self.assertTrue(all(len(row) == 3 and all(cell for cell in row) for row in rows))

    def test_related_layers_reference_one_canonical_contract(self) -> None:
        for path in (FRONT_DOOR, SUPERVISOR_REFERENCE, ORCHESTRATOR, AUTOPILOT, REVIEW, PROTOCOL):
            text = path.read_text(encoding="utf-8")
            self.assertIn("supervisor-judgment.md", text, path.as_posix())
        front_door = FRONT_DOOR.read_text(encoding="utf-8")
        self.assertIn("one concrete question", front_door)
        self.assertIn("marginal value is low", front_door)

    def test_bilingual_readmes_publish_the_same_new_capability(self) -> None:
        english = README_EN.read_text(encoding="utf-8")
        vietnamese = README_VI.read_text(encoding="utf-8")
        self.assertIn("## Judgment-aware supervision", english)
        self.assertIn("## Giám sát có judgment", vietnamese)
        for text in (english, vietnamese):
            self.assertIn("tradeoff", text.lower())
            self.assertIn("owner", text.lower())
            self.assertIn("diminishing", text.lower())
        self.assertRegex(english, r"English \| \[Tiếng Việt\]\(README-vi\.md\)")
        self.assertRegex(vietnamese, r"\[English\]\(README\.md\) \| Tiếng Việt")


if __name__ == "__main__":
    unittest.main()
