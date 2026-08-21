"""Run a pool's X-ray against the open web and return real profiles.

X-ray search is how sourcers have always reached LinkedIn without a seat:
you ask a search engine for pages on linkedin.com/in that match your terms.
This does the same thing through a search engine's official API instead of
by hand, which is the difference between a string you paste and a tool that
returns people.

It deliberately does not touch LinkedIn directly. Automated requests to
LinkedIn get accounts banned, and a recruiter's account is their livelihood.
Search engines index those pages and sell API access to their index; that is
the supported path and it is the one this uses.

Backends, in the order they are tried:
  SearXNG            no key, no signup, the default
  Brave Search API   BRAVE_API_KEY      if you want higher volume
  Serper (Google)    SERPER_API_KEY
  Google CSE         GOOGLE_API_KEY + GOOGLE_CSE_ID

SearXNG is the default deliberately. It is open-source metasearch with public
instances that expose a JSON endpoint for exactly this purpose, which means
this works the moment you clone it - no account, no key, no card. The keyed
backends exist for when you are running enough volume that a public instance
would be rude.
"""

# Public SearXNG instances that expose JSON. Tried in order; the first that
# answers wins. Kept short on purpose - hammering these is bad manners.
SEARX_INSTANCES = (
    "https://search.inetol.net",
    "https://searxng.world",
    "https://baresearch.org",
    "https://search.rhscz.eu",
    "https://opnxng.com",
    "https://searx.tiekoetter.com",
    "https://search.bus-hit.me",
    "https://searx.be",
    "https://priv.au",
)

import os
import re
from dataclasses import dataclass

import httpx

from src.marketmap import strings


class WebError(RuntimeError):
    """No search backend is configured, or the one configured refused."""


@dataclass
class Hit:
    title: str
    url: str
    snippet: str = ""

    @property
    def is_profile(self) -> bool:
        return "/in/" in self.url

    @property
    def handle(self) -> str:
        m = re.search(r"/in/([^/?#]+)", self.url)
        return m.group(1) if m else ""

    @property
    def person(self) -> str:
        """LinkedIn titles arrive as 'Name - Headline - Company | LinkedIn'."""
        t = re.sub(r"\s*[|\-]\s*LinkedIn\s*$", "", self.title).strip()
        return t.split(" - ")[0].strip() if " - " in t else t

    @property
    def headline(self) -> str:
        t = re.sub(r"\s*[|\-]\s*LinkedIn\s*$", "", self.title).strip()
        return t.split(" - ", 1)[1].strip() if " - " in t else ""


def available() -> str:
    """Always returns something: SearXNG needs no configuration."""
    if os.environ.get("BRAVE_API_KEY"):
        return "brave"
    if os.environ.get("SERPER_API_KEY"):
        return "serper"
    if os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"):
        return "google"
    return "searx"


def _searx(q: str, n: int, client) -> list[Hit]:
    """Try public instances until one answers.

    They rate-limit, go down, and rotate. That is the price of needing no
    account, so the list is long and any single failure is uninteresting.
    """
    last = None
    for base in SEARX_INSTANCES:
        try:
            r = client.get(f"{base}/search",
                           params={"q": q, "format": "json"},
                           headers={"User-Agent": "talent-market-map"})
            if r.status_code >= 400:
                last = f"{base} returned {r.status_code}"
                continue
            results = r.json().get("results") or []
            if results:
                return [Hit(h.get("title", ""), h.get("url", ""),
                            h.get("content", "")) for h in results[:n]]
            last = f"{base} returned nothing"
        except (httpx.HTTPError, ValueError) as exc:
            last = f"{base}: {exc}"
    raise WebError(f"no SearXNG instance answered ({last}). "
                   f"Set BRAVE_API_KEY for a dedicated backend.")


def _brave(q: str, n: int, client) -> list[Hit]:
    r = client.get("https://api.search.brave.com/res/v1/web/search",
                   params={"q": q, "count": min(n, 20)},
                   headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"],
                            "Accept": "application/json"})
    r.raise_for_status()
    return [Hit(h.get("title", ""), h.get("url", ""), h.get("description", ""))
            for h in (r.json().get("web", {}).get("results") or [])]


def _serper(q: str, n: int, client) -> list[Hit]:
    r = client.post("https://google.serper.dev/search",
                    json={"q": q, "num": min(n, 20)},
                    headers={"X-API-KEY": os.environ["SERPER_API_KEY"]})
    r.raise_for_status()
    return [Hit(h.get("title", ""), h.get("link", ""), h.get("snippet", ""))
            for h in (r.json().get("organic") or [])]


def _google(q: str, n: int, client) -> list[Hit]:
    r = client.get("https://www.googleapis.com/customsearch/v1",
                   params={"key": os.environ["GOOGLE_API_KEY"],
                           "cx": os.environ["GOOGLE_CSE_ID"],
                           "q": q, "num": min(n, 10)})
    r.raise_for_status()
    return [Hit(h.get("title", ""), h.get("link", ""), h.get("snippet", ""))
            for h in (r.json().get("items") or [])]


_BACKENDS = {"searx": _searx, "brave": _brave,
             "serper": _serper, "google": _google}


def search(query: str, *, limit: int = 10, backend=None, client=None) -> list[Hit]:
    backend = backend or available()
    fn = _BACKENDS.get(backend) if isinstance(backend, str) else backend
    if fn is None:
        raise WebError(f"unknown search backend: {backend}")

    owned = client is None
    http = client or httpx.Client(timeout=30)
    try:
        return fn(query, limit, http)
    except httpx.HTTPStatusError as exc:
        raise WebError(f"{backend} returned {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise WebError(f"could not reach {backend}: {exc}") from exc
    finally:
        if owned:
            http.close()


def search_pool(pool, *, site: str = "linkedin.com/in", limit: int = 10,
                backend=None, client=None) -> list[Hit]:
    """Run this pool's X-ray and return the profiles it found."""
    hits = search(strings.xray(pool, site=site), limit=limit,
                  backend=backend, client=client)
    seen, out = set(), []
    for h in hits:
        if not h.is_profile or h.handle in seen:
            continue
        seen.add(h.handle)
        out.append(h)
    return out


def render(pool, hits: list[Hit]) -> str:
    out = [f"{pool.name}  -  {len(hits)} profiles", ""]
    if not hits:
        out.append("  (nothing returned; the pool's terms may be too narrow)")
    for i, h in enumerate(hits, 1):
        out.append(f"{i:2}. {h.person}")
        if h.headline:
            out.append(f"    {h.headline}")
        out.append(f"    {h.url}")
        if h.snippet:
            out.append(f"    \"{h.snippet.strip()[:180]}\"")
        out.append("")
    return "\n".join(out)


def open_in_browser(pools, site: str = "linkedin.com/in", engine: str = "google") -> list[str]:
    """Open each pool's X-ray as a real search in your own browser.

    The keyless path, and the one that always works. Automated search needs a
    key or a public instance that will rate-limit you; a browser needs neither
    because it is you, running a search you were going to run anyway, in your
    own session. Nothing is scraped and nothing can be blocked.
    """
    import subprocess
    import urllib.parse

    base = {"google": "https://www.google.com/search?q=",
            "bing": "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q="}.get(engine)
    if not base:
        raise WebError(f"unknown engine: {engine}")

    urls = []
    for pool in pools:
        q = strings.xray(pool, site=site)
        url = base + urllib.parse.quote_plus(q)
        urls.append(url)
        subprocess.run(["open", url], check=False)
    return urls


__all__ = ["Hit", "WebError", "available", "open_in_browser", "render",
           "search", "search_pool"]
