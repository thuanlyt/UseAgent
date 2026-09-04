# ADR-0007: Visual documentation system

- `Status`: accepted
- `Date`: 2026-09-04
- `Owner`: supervisor

## Context

UseAgent is a coordination system with several related ledgers and runtime
roles. Text-only documentation makes the relationship between supervisor,
workers, mailboxes, evidence and checkpoints unnecessarily hard to scan. The
docs site also needs a shareable visual identity without adding a JavaScript
framework, third-party fonts, analytics or render-blocking dependencies.

## Decision

Add a small visual layer next to the source-anchored Markdown:

- one generated, text-free hero illustration for the docs homepage and social
  preview, with a WebP derivative for fast delivery and a PNG fallback;
- three repository-owned SVG diagrams for the supervisor loop, shared ledger
  and multi-runtime handoff;
- semantic `<figure>`/`<img>` markup with descriptive alt text, explicit
  dimensions, captions and lazy loading for below-the-fold images;
- local assets only, with no tracking pixels, remote image hosts or external
  font dependency.

The diagrams explain concepts but never replace the CLI, registry, contracts or
knowledge cards as the source of truth. The generated hero contains no words,
logos or third-party marks and is stored in the repository as a project asset.

## Consequences

- New users can understand the control-plane relationships before reading all
  of the operational detail.
- SVG diagrams stay crisp, searchable through nearby text and small enough for
  fast static delivery; the hero uses a 48 KB WebP derivative above the fold,
  with the larger PNG retained for fallback/social compatibility.
- Any future visual must carry alt text, dimensions, responsive behavior and a
  documented source/license decision before publication.

## Source anchors

- `docs-site/assets/useagent-supervisor-loop.svg`
- `docs-site/assets/useagent-shared-ledger.svg`
- `docs-site/assets/useagent-runtime-handoff.svg`
- `docs-site/assets/useagent-control-plane-hero.png`
- `docs-site/assets/useagent-control-plane-hero.webp`
- `docs-site/index.html`
- `docs-site/build.py`
- `tests/docs_site/test_docs_site.py:test_visual_asset_contract`
