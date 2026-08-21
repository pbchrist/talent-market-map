"""Search the web by driving a real browser.

Scripts that imitate a browser get blocked: Google refuses them, Mojeek
returns 403, DuckDuckGo's HTML endpoint throttles after a handful of
requests, and every public SearXNG instance rate-limits. All of that was
measured, not assumed.

A real browser is not blocked, because it is not pretending. This drives an
actual Chrome through the same searches a recruiter would run by hand. No
API key, no account, no card, no scraping of LinkedIn itself - it reads a
search engine's results page, which is what X-ray sourcing has always been.

Keep the volume human. This is a tool for working a req, not a crawler.
"""

import re
import urllib.parse
from dataclasses import dataclass

ENGINES = {
    "duckduckgo": "https://duckduckgo.com/?q=",
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
}


class BrowserError(RuntimeError):
    """Playwright is missing, or no browser could be driven."""


@dataclass
class Profile:
    url: str
    title: str = ""
    snippet: str = ""

    @property
    def handle(self) -> str:
        m = re.search(r"/in/([^/?#]+)", self.url)
        return m.group(1) if m else ""

    @property
    def person(self) -> str:
        t = re.sub(r"\s*[|\-]\s*LinkedIn.*$", "", self.title).strip()
        return t.split(" - ")[0].strip() if " - " in t else t

    @property
    def headline(self) -> str:
        t = re.sub(r"\s*[|\-]\s*LinkedIn.*$", "", self.title).strip()
        return t.split(" - ", 1)[1].strip() if " - " in t else ""


def _extract(page, site: str) -> list[Profile]:
    """Pull result links out of whatever the engine rendered.

    Engines wrap results differently and change markup often, so this asks
    the DOM for anchors pointing at the target site rather than matching a
    specific result-card class that will break next month.
    """
    host = site.split("/")[0]
    rows = page.eval_on_selector_all(
        f"a[href*='{host}'], a[href*='uddg']",
        """els => els.map(e => ({
              href: e.href,
              text: (e.innerText || '').trim(),
              near: (e.closest('article, li, div[data-testid], .result')?.innerText || '').trim()
           }))""")
    out, seen = [], set()
    for r in rows:
        href = r.get("href", "")
        # DuckDuckGo wraps some results in a redirect; the real target sits in
        # the uddg parameter. Unwrap before deciding whether to keep it.
        if "uddg=" in href:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            href = (q.get("uddg") or [href])[0]
        href = re.sub(r"[?#].*$", "", href)
        if site not in href or href in seen:
            continue
        seen.add(href)
        text = r.get("text") or ""
        near = r.get("near") or ""
        lines = [l for l in near.split("\n") if l.strip()]
        title = next((l for l in lines if " - " in l or "|" in l), text or (lines[0] if lines else ""))
        snippet = lines[-1] if len(lines) > 2 else ""
        out.append(Profile(url=href, title=title.strip(), snippet=snippet.strip()[:200]))
    return out


def search(query: str, *, site: str = "linkedin.com/in", engine: str = "duckduckgo",
           limit: int = 10, headless: bool = True, pause_ms: int = 3500) -> list[Profile]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserError(
            "Playwright is not installed. pip install playwright") from exc

    base = ENGINES.get(engine)
    if not base:
        raise BrowserError(f"unknown engine: {engine}")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chrome", headless=headless)
        except Exception:
            browser = pw.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            page.goto(base + urllib.parse.quote_plus(query),
                      wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(pause_ms)
            return _extract(page, site)[:limit]
        finally:
            browser.close()


def search_pool(pool, *, site: str = "linkedin.com/in", limit: int = 10,
                engine: str = "duckduckgo", headless: bool = False) -> list[Profile]:
    """Run this pool's searches.

    Deliberately several narrow queries rather than one enormous boolean: a
    three-group X-ray with a dozen ORs returns nothing on most engines, while
    the same intent split into title-plus-company pairs returns people.
    """
    found: dict[str, Profile] = {}
    titles = pool.titles[:3] or [pool.name]
    anchors = (pool.companies[:3] or []) + (pool.signals[:2] or [])

    for title in titles:
        for anchor in (anchors or [""]):
            q = f'site:{site} "{title}"' + (f' "{anchor}"' if anchor else "")
            try:
                for p in search(q, site=site, engine=engine,
                                limit=limit, headless=headless):
                    found.setdefault(p.handle or p.url, p)
            except BrowserError:
                raise
            except Exception:
                continue
            if len(found) >= limit:
                return list(found.values())[:limit]
    return list(found.values())[:limit]


def render(pool, profiles: list[Profile]) -> str:
    out = [f"{pool.name}  -  {len(profiles)} profiles", ""]
    if not profiles:
        out.append("  (nothing returned)")
    for i, p in enumerate(profiles, 1):
        out.append(f"{i:2}. {p.person or p.handle}")
        if p.headline:
            out.append(f"    {p.headline}")
        out.append(f"    {p.url}")
        if p.snippet:
            out.append(f"    \"{p.snippet}\"")
        out.append("")
    return "\n".join(out)


__all__ = ["BrowserError", "ENGINES", "Profile", "render", "search", "search_pool"]
