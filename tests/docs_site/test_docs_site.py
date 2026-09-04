from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs-site"


class DocsSiteTests(unittest.TestCase):
    def test_static_build_and_page_contract(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SITE / "build.py"), "--check-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VALIDATED", result.stdout)
        pages = sorted(SITE.glob("*.html"))
        self.assertEqual(len(pages), 6)
        for page in pages:
            content = page.read_text(encoding="utf-8")
            self.assertIn("<meta name=\"description\"", content, page.name)
            self.assertIn('href="#main-content"', content, page.name)
            self.assertIn('id="main-content"', content, page.name)
            if "https://" in content:
                self.assertIn('rel="noreferrer"', content, page.name)


if __name__ == "__main__":
    unittest.main()
