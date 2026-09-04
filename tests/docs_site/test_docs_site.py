from __future__ import annotations

from html.parser import HTMLParser
import json
import subprocess
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs-site"
PRIMARY_ORIGIN = "https://useagent.thuanlyt.id.vn"
INDEXABLE_URLS = {
    "index.html": f"{PRIMARY_ORIGIN}/",
    "getting-started.html": f"{PRIMARY_ORIGIN}/getting-started.html",
    "architecture.html": f"{PRIMARY_ORIGIN}/architecture.html",
    "operations.html": f"{PRIMARY_ORIGIN}/operations.html",
    "vi.html": f"{PRIMARY_ORIGIN}/vi.html",
}


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
        self.links: list[dict[str, str]] = []
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
        elif tag == "link":
            self.links.append(attributes)
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
            self.assertNotIn("style=", content, page.name)
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
                self.assertEqual(meta_by_property.get("og:url"), INDEXABLE_URLS[page.name], page.name)
                self.assertTrue(meta_by_property.get("og:site_name", "").strip(), page.name)
                self.assertTrue(meta_by_property.get("og:locale", "").strip(), page.name)
                self.assertTrue(meta_by_name.get("twitter:title", "").strip(), page.name)
                self.assertTrue(meta_by_name.get("twitter:description", "").strip(), page.name)
            if page.name == "404.html":
                self.assertEqual(meta_by_name.get("robots"), "noindex", page.name)
            if page.name == "index.html":
                search_inputs = [item for item in parser.inputs if item.get("id") == "doc-search"]
                self.assertEqual(len(search_inputs), 1, page.name)
                self.assertEqual(search_inputs[0].get("role"), "combobox", page.name)
                self.assertEqual(len(parser.jsonld), 1, page.name)
                structured_data = json.loads(parser.jsonld[0])
                self.assertEqual(structured_data["@type"], "SoftwareSourceCode")
                self.assertEqual(
                    structured_data["codeRepository"],
                    "https://github.com/thuanlyt/UseAgent",
                )
                self.assertEqual(structured_data["url"], INDEXABLE_URLS[page.name])

        styles = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", styles)
        self.assertIn("@media (max-width: 800px)", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)
        self.assertIn("--color-secondary: #52627a", styles)

    def test_production_seo_contract(self) -> None:
        expected_alternates = {
            "index.html": {
                "en": INDEXABLE_URLS["index.html"],
                "vi": INDEXABLE_URLS["vi.html"],
                "x-default": INDEXABLE_URLS["index.html"],
            },
            "getting-started.html": {
                "en": INDEXABLE_URLS["getting-started.html"],
                "x-default": INDEXABLE_URLS["getting-started.html"],
            },
            "architecture.html": {
                "en": INDEXABLE_URLS["architecture.html"],
                "x-default": INDEXABLE_URLS["architecture.html"],
            },
            "operations.html": {
                "en": INDEXABLE_URLS["operations.html"],
                "x-default": INDEXABLE_URLS["operations.html"],
            },
            "vi.html": {
                "en": INDEXABLE_URLS["index.html"],
                "vi": INDEXABLE_URLS["vi.html"],
                "x-default": INDEXABLE_URLS["index.html"],
            },
        }
        for filename, canonical in INDEXABLE_URLS.items():
            parser = SiteContractParser()
            parser.feed((SITE / filename).read_text(encoding="utf-8"))
            alternates = {
                link.get("hreflang"): link.get("href")
                for link in parser.links
                if link.get("rel") == "alternate" and link.get("hreflang")
            }
            self.assertEqual(alternates, expected_alternates[filename], filename)
            canonical_links = [
                link.get("href")
                for link in parser.links
                if link.get("rel") == "canonical"
            ]
            self.assertEqual(canonical_links, [canonical], filename)

        sitemap_root = ElementTree.fromstring((SITE / "sitemap.xml").read_text(encoding="utf-8"))
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        self.assertEqual(sitemap_root.tag, f"{namespace}urlset")
        sitemap_urls = [node.text for node in sitemap_root.findall(f"{namespace}url/{namespace}loc")]
        self.assertEqual(sitemap_urls, list(INDEXABLE_URLS.values()))
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn(f"Sitemap: {PRIMARY_ORIGIN}/sitemap.xml", robots)

    def test_mobile_layout_prevents_content_overflow(self) -> None:
        styles = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(styles, r"\.hero-copy, \.hero-visual\s*\{[^}]*min-width:\s*0")
        self.assertIn("grid-template-columns: 1.5rem minmax(0,1fr) auto", styles)
        self.assertIn("grid-template-columns: 3rem minmax(0,1fr)", styles)
        self.assertIn("grid-template-columns: 2.5rem minmax(0,1fr)", styles)
        self.assertRegex(styles, r"\.article-layout > \*\s*\{[^}]*min-width:\s*0")
        self.assertIn("@media (max-width: 520px)", styles)
        self.assertRegex(styles, r"\.hero-actions\s*\{[^}]*flex-direction:\s*column")
        self.assertRegex(styles, r"\.hero-actions \.button\s*\{[^}]*width:\s*100%")
        self.assertRegex(styles, r"\.hero h1\s*\{[^}]*font-size:\s*clamp\(2\.6rem,12vw,3\.8rem\)")

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
        self.assertEqual(headers["Permissions-Policy"], "camera=(), geolocation=(), microphone=()")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("style-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("fonts.googleapis.com", headers["Content-Security-Policy"])

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
