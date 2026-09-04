# UseAgent documentation site

This is a dependency-light static site for the UseAgent public documentation.
It intentionally uses plain HTML, CSS and browser JavaScript so the first
preview is fast, inspectable and deployable to Vercel as static output.

## Local build

From the repository root:

```powershell
python docs-site/build.py --check-only
python docs-site/build.py --output dist
python -m http.server 4173 --directory docs-site/dist
```

Open `http://localhost:4173`. The build validates local HTML links before
copying the static assets into the ignored `docs-site/dist/` directory.

## Why static-first

The site deliberately avoids a client-rendered framework: every document is
available as crawlable HTML, the only browser JavaScript is the small local
search/menu enhancement, and Vercel can serve the output directly from its
edge cache. This keeps the critical path small while preserving deep links,
keyboard navigation and graceful behavior when JavaScript is unavailable.

The confirmed SEO origin is `https://useagent.thuanlyt.id.vn/`. The five
indexable pages publish absolute canonical and EN/VI alternate metadata;
`robots.txt` references `sitemap.xml`. The `vercel.app` hostname remains a
deployment fallback rather than a second SEO source of truth.

## Visual asset contract

The local `assets/` directory contains the visual layer used by the site:

- `useagent-control-plane-hero.webp` — optimized above-the-fold hero delivery;
- `useagent-control-plane-hero.png` — generated text-free fallback and social image;
- `useagent-supervisor-loop.svg` — goal → supervisor → worker → QA loop;
- `useagent-shared-ledger.svg` — knowledge, work, evidence and checkpoint memory;
- `useagent-runtime-handoff.svg` — Codex, Claude Code and Antigravity on one protocol.

Every page image has explicit `alt`, `width` and `height` attributes. The
homepage hero is eager because it is above the fold; article diagrams are
lazy-loaded. Keep future assets local, lightweight and free of tracking pixels,
remote image hosts or unreviewed third-party marks. The visual source of truth
is [ADR-0007](../knowledge/decisions/0007-visual-documentation-system.md).

## Design contract

The persisted source of truth is
`../design-system/useagent-docs/MASTER.md`, generated with the UI/UX Pro Max
design-system workflow. The current direction is Minimalism/Swiss: a system
sans stack for body copy, a system mono stack for headings and code, a
slate/blue high-contrast palette, restrained motion, visible keyboard focus
and responsive layouts at 375px, 768px, 1024px and 1440px. System fonts are
intentional: they keep the critical path free of third-party font requests.

The content foundation now includes English and Vietnamese journeys, runtime
examples and operator guidance. Final browser visual QA, hosting and DNS remain
separate, explicitly gated operations.

Read [DEPLOYMENT.md](DEPLOYMENT.md) for the Vercel preview, exact-domain
Cloudflare gate and rollback runbook.
