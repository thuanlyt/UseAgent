from __future__ import annotations

from html.parser import HTMLParser
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs-site"


class SiteContractParser(HTMLParser):
    """Collect the small semantic contract that can be checked without a browser."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.title_text = ""
        self._in_title = False
        self.meta: list[dict[str, str]] = []
        self.main_ids: list[str] = []
        self.h1_count = 0
        self.labels_for: set[str] = set()
        self.buttons: list[tuple[dict[str, str], str]] = []
        self._active_button: dict[str, str] | None = None
        self._active_button_text = ""
        self.inputs: list[dict[str, str]] = []
        self.navs: list[dict[str, str]] = []
        self.external_links: list[dict[str, str]] = []
        self.jsonld: list[str] = []
        self._active_jsonld = False
        self._jsonld_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_lang = attributes.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.meta.append(attributes)
        elif tag == "main":
            self.main_ids.append(attributes.get("id", ""))
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "label":
            label_for = attributes.get("for")
            if label_for:
                self.labels_for.add(label_for)
        elif tag == "button":
            self._active_button = attributes
            self._active_button_text = ""
        elif tag == "input":
            self.inputs.append(attributes)
        elif tag == "nav":
            self.navs.append(attributes)
        elif tag == "script" and attributes.get("type") == "application/ld+json":
            self._active_jsonld = True
            self._jsonld_text = ""
        elif tag == "a":
            href = attributes.get("href", "")
            if href.startswith(("https://", "http://", "//")):
                self.external_links.append(attributes)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "button" and self._active_button is not None:
            self.buttons.append((self._active_button, self._active_button_text))
            self._active_button = None
            self._active_button_text = ""
        elif tag == "script" and self._active_jsonld:
            self.jsonld.append(self._jsonld_text)
            self._active_jsonld = False
            self._jsonld_text = ""

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text += data
        if self._active_button is not None:
            self._active_button_text += data
        if self._active_jsonld:
            self._jsonld_text += data


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

    def test_semantic_accessibility_and_responsive_contract(self) -> None:
        pages = sorted(SITE.glob("*.html"))
        for page in pages:
            parser = SiteContractParser()
            parser.feed(page.read_text(encoding="utf-8"))
            meta_by_name = {
                item.get("name", "").lower(): item.get("content", "")
                for item in parser.meta
                if item.get("name")
            }
            meta_by_property = {
                item.get("property", "").lower(): item.get("content", "")
                for item in parser.meta
                if item.get("property")
            }
            self.assertIn(parser.html_lang, {"en", "vi"}, page.name)
            self.assertTrue(parser.title_text.strip(), page.name)
            self.assertIn("viewport", meta_by_name, page.name)
            self.assertIn("width=device-width", meta_by_name["viewport"], page.name)
            self.assertTrue(meta_by_name.get("description", "").strip(), page.name)
            self.assertEqual(parser.main_ids, ["main-content"], page.name)
            self.assertEqual(parser.h1_count, 1, page.name)
            for button, button_text in parser.buttons:
                self.assertTrue(
                    button.get("aria-label") or button.get("aria-labelledby") or button_text.strip(),
                    page.name,
                )
            for input_attributes in parser.inputs:
                if input_attributes.get("type", "text").lower() == "hidden":
                    continue
                self.assertTrue(
                    input_attributes.get("aria-label")
                    or input_attributes.get("aria-labelledby")
                    or input_attributes.get("id") in parser.labels_for,
                    page.name,
                )
            for nav in parser.navs:
                self.assertTrue(nav.get("aria-label") or nav.get("aria-labelledby"), page.name)
            for link in parser.external_links:
                self.assertIn("noreferrer", link.get("rel", "").split(), page.name)
            if page.name != "404.html":
                self.assertTrue(meta_by_property.get("og:title", "").strip(), page.name)
                self.assertTrue(meta_by_property.get("og:description", "").strip(), page.name)
                self.assertEqual(meta_by_property.get("og:type"), "website", page.name)
                self.assertEqual(meta_by_name.get("twitter:card"), "summary", page.name)
                self.assertNotIn("og:url", meta_by_property, page.name)
            if page.name == "404.html":
                self.assertEqual(meta_by_name.get("robots"), "noindex", page.name)
            if page.name == "index.html":
                self.assertEqual(len(parser.jsonld), 1, page.name)
                structured_data = json.loads(parser.jsonld[0])
                self.assertEqual(structured_data["@type"], "SoftwareSourceCode")
                self.assertEqual(
                    structured_data["codeRepository"],
                    "https://github.com/thuanlyt/UseAgent",
                )
                self.assertNotIn("url", structured_data)

        styles = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", styles)
        self.assertIn("@media (max-width: 800px)", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)

    def test_hosting_dry_run_contract(self) -> None:
        vercel = json.loads((SITE / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(vercel["buildCommand"], "python3 build.py --output dist")
        self.assertEqual(vercel["outputDirectory"], "dist")
        self.assertTrue(vercel["cleanUrls"])
        self.assertFalse(vercel["trailingSlash"])
        headers = {
            header["key"]: header["value"]
            for rule in vercel["headers"]
            for header in rule["headers"]
        }
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

        runbook = (SITE / "DEPLOYMENT.md").read_text(encoding="utf-8").lower()
        for required_phrase in (
            "preview deployment",
            "exact hostname",
            "cloudflare",
            "rollback",
            "no environment secret",
        ):
            self.assertIn(required_phrase, runbook)
        self.assertNotIn("vercel_token=", runbook)
        self.assertNotIn("cloudflare_api_token=", runbook)


if __name__ == "__main__":
    unittest.main()
