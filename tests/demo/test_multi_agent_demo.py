from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "examples" / "multi-agent-demo" / "run_demo.py"


class MultiAgentDemoTests(unittest.TestCase):
    def test_demo_completes_without_external_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, str(DEMO)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)
        self.assertIn("assignment -> pull -> report -> ingest -> QA -> checkpoint", result.stdout)


if __name__ == "__main__":
    unittest.main()
