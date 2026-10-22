# AGENTS.md — talent-market-map

Rules for any AI working here (Claude, Hermes, Grok Bot, ChatGPT). Short on purpose. The README has the full story.

## What this is

Paste a job description. It works out the capability underneath the title, finds the industries where people build that capability without holding the title, and hands back the searches that find them. No install, no database, no scraping, no candidate data. Web app in `docs/` (GitHub Pages: https://pbchrist.github.io/talent-market-map/); CLI in `src/marketmap/`.

## Run and test

- Tests: `pytest` (fully offline; one test runs `tests/js/endpoint_guard.test.js` with node and skips itself if node is missing).
- CLI: `python -m src.marketmap.cli --title "<title>" --role jd.txt` (flags in README). The model endpoint comes from `TMM_LLM_BASE_URL` / `TMM_LLM_MODEL`.

## Where things live

`src/marketmap/` (engine; all Boolean/X-ray syntax in `strings.py`) · `docs/` (the published site; everything in it goes live) · `maps/` (saved maps, reused per market) · `tests/` · `DECISIONS.md` · `DONE.md` · `STABLE-STATE-2026-08-21.md`. DECISIONS and DONE sit at the root so they never land on the Pages site.

## Hard rules (from README)

- The model supplies judgement; code supplies syntax. Never let the model emit Boolean or X-ray strings.
- LinkedIn itself is never touched; search reads a search engine's results page in a real browser.
- Keep browser search at human volume. A tool for working a req, not a crawler.
- No candidate data stored in the repo. Tests stay offline.

## Workflow (every task)

1. **Ticket first.** 3–4 lines: what changes, and how we'll know it worked.
2. **Preflight.** Right branch, `git status` clean, `pytest` green before you start.
3. **One change = one branch = one PR.** Never push or merge to `main` without Patrick's yes. (Merging changes in `docs/` publishes them.)
4. **Builder doesn't grade its own work.** Proof = the checks in `DONE.md`, confirmed by someone else (QA bot or Patrick).
5. **Lasting decisions** go in `DECISIONS.md`, dated and sourced. A new rule replaces the old one; never stack.
6. **Stop when done.** No bonus refactors, no follow-on audits.
