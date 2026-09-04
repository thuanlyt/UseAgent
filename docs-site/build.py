#!/usr/bin/env python3
"""Build and validate the dependency-light static UseAgent docs site."""

from __future__ import annotations

import argparse
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_ROOT = Path(__file__).resolve().parent
STATIC_SUFFIXES = {".html", ".css", ".js", ".svg", ".txt", ".xml", ".webmanifest"}
SKIP_PARTS = {"dist", ".git"}


class LocalLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def source_files() -> list[Path]:
    return [path for path in SITE_ROOT.rglob("*") if path.is_file() and not any(part in SKIP_PARTS for part in path.relative_to(SITE_ROOT).parts) and path.suffix.lower() in STATIC_SUFFIXES]


def check_links(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        if source.suffix.lower() != ".html":
            continue
        parser = LocalLinkParser()
        parser.feed(source.read_text(encoding="utf-8"))
        for raw_target in parser.targets:
            parsed = urlsplit(raw_target)
            if not parsed.path or parsed.scheme or parsed.netloc or raw_target.startswith(("//", "mailto:", "tel:", "javascript:")):
                continue
            relative = unquote(parsed.path).lstrip("/")
            target = SITE_ROOT / relative if raw_target.startswith("/") else source.parent / relative
            if target.is_dir():
                target /= "index.html"
            if not target.exists():
                errors.append(f"{source.relative_to(SITE_ROOT)} -> {raw_target}")
    return errors


def build(output: Path) -> int:
    output = output.resolve()
    try:
        output.relative_to(SITE_ROOT.resolve())
    except ValueError as exc:
        raise SystemExit("output must stay inside docs-site") from exc
    if output == SITE_ROOT.resolve():
        raise SystemExit("output must be a child directory of docs-site")
    files = source_files()
    errors = check_links(files)
    if errors:
        print("BROKEN LINKS")
        for error in errors:
            print(f"- {error}")
        return 1
    output.mkdir(parents=True, exist_ok=True)
    for source in files:
        destination = output / source.relative_to(SITE_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f"BUILT {len(files)} static files to {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist", help="child directory under docs-site")
    parser.add_argument("--check-only", action="store_true", help="validate local links without copying")
    args = parser.parse_args()
    files = source_files()
    errors = check_links(files)
    if errors:
        print("BROKEN LINKS")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.check_only:
        print(f"VALIDATED {len(files)} static files")
        return 0
    return build(SITE_ROOT / args.output)


if __name__ == "__main__":
    raise SystemExit(main())
