from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPOSITORY_ROOT / "examples" / "multi-runtime-conformance" / "run_conformance.py"


class MultiRuntimeConformanceTests(unittest.TestCase):
    def test_three_runtime_identities_share_the_public_protocol(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HARNESS)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Codex + Claude Code + Antigravity", result.stdout)
        self.assertIn("assignment -> pull -> report -> ingest -> QA -> checkpoint", result.stdout)


if __name__ == "__main__":
    unittest.main()
