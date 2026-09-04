---
type: useagent-assignment
task_id: UA-0036
agent: supervisor
created_at: 2026-09-04T13:20:59Z
scope: ["docs-site", "tests/docs_site"]
---

# Assignment UA-0036: Close production SEO metadata and discoverability gaps

You are the assigned worker. Use `$useagent-worker` and do not modify files outside the scope below.

## Objective

Add a primary-domain canonical strategy, sitemap and robots sitemap reference, bilingual hreflang/locale metadata, and complete social preview metadata without introducing guessed domains or secrets.

## Scope

- `docs-site`
- `tests/docs_site`

## Dependencies

UA-0035

## Acceptance

- [ ] All five indexable pages publish an absolute canonical URL on useagent.thuanlyt.id.vn; sitemap.xml lists every indexable route and robots.txt references it; EN/VI alternate links and locale metadata are consistent; Open Graph URL/title/description and Twitter title/description are present; metadata regression tests cover the contract; local build, validator, unit tests and live final-host smoke remain green.

## Verification

- `python -m unittest discover -s tests -v`
- `python docs-site/build.py --check-only`
- `python tools/useagent.py validate`
- `live HTTP metadata and sitemap smoke on https://useagent.thuanlyt.id.vn`

## Read first

- `AGENTS.md`
- `knowledge/INDEX.md`
- `work/items/UA-0036.md`

## Required report

Run `python tools/useagent.py task report UA-0036 --agent supervisor --result completed --summary "..." --next-action "Review"`.
Include changed files, checks/evidence and blockers. The supervisor will review before done.

## Assignment path

`work/agents/supervisor/inbox/UA-0036.md`
