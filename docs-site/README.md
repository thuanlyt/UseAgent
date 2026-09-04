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

## Design contract

The persisted source of truth is
`../design-system/useagent-docs/MASTER.md`, generated with the UI/UX Pro Max
design-system workflow. The current direction is Minimalism/Swiss: IBM Plex
Sans for body copy, JetBrains Mono for headings and code, a slate/blue
high-contrast palette, restrained motion, visible keyboard focus and responsive
layouts at 375px, 768px, 1024px and 1440px.

The content foundation now includes English and Vietnamese journeys, runtime
examples and operator guidance. Final browser visual QA, hosting and DNS remain
separate, explicitly gated operations.

Read [DEPLOYMENT.md](DEPLOYMENT.md) for the Vercel preview, exact-domain
Cloudflare gate and rollback runbook.
