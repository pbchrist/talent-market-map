"""Pool -> actual people, via the GitHub API.

This is the step that makes a map do work. A map tells you which markets to
search; this searches one of them and comes back with humans.

Two decisions matter here.

It searches repositories, not bios. Bio search finds people who describe
themselves a certain way, which is the same title-matching problem one level
down. Repository search finds people who have actually built the thing, and
their repo is the evidence. That is the whole premise of the map applied to
individuals: judge the work, not the label.

It uses the official API. No scraping, no rate-limit evasion, no ToS
surface. GitHub gives this away for free and it is the single best public
record of what a technical person can actually do.
"""

import json
import os
import subprocess
from dataclasses import dataclass, field

import httpx

API = "https://api.github.com"

# Signals that are real languages get a language: qualifier, which is far
# more precise than the same word as free text.
_LANGS = {
    "c++": "C%2B%2B", "c#": "C%23", "python": "Python", "rust": "Rust",
    "go": "Go", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "glsl": "GLSL", "hlsl": "HLSL", "cuda": "Cuda",
}


class FindError(RuntimeError):
    """GitHub could not be reached, or refused the query."""


@dataclass
class Candidate:
    login: str
    url: str
    name: str | None = None
    location: str | None = None
    company: str | None = None
    bio: str | None = None
    public_repos: int = 0
    followers: int = 0
    evidence: list[str] = field(default_factory=list)   # repos that matched
    matched: list[str] = field(default_factory=list)    # which signals hit

    @property
    def score(self) -> int:
        """Distinct signals matched. Deliberately not a percentage: this
        ranks who to look at first, it does not judge anybody."""
        return len(set(self.matched))


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _get(path: str, client: httpx.Client | None = None) -> dict:
    owned = client is None
    tok = _token()
    headers = {"Accept": "application/vnd.github+json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    http = client or httpx.Client(timeout=30, headers=headers)
    try:
        r = http.get(f"{API}{path}" if path.startswith("/") else path)
    except httpx.HTTPError as exc:
        raise FindError(f"could not reach GitHub: {exc}") from exc
    finally:
        if owned:
            http.close()
    if r.status_code == 403:
        raise FindError("GitHub rate limit hit. Wait, or set GITHUB_TOKEN.")
    if r.status_code >= 400:
        raise FindError(f"GitHub returned {r.status_code}: {r.text[:160]}")
    return r.json()


def queries(pool, max_signals: int = 6) -> list[tuple[str, str]]:
    """Build one repo-search query per signal. Returns (signal, query)."""
    out = []
    for sig in pool.signals[:max_signals]:
        s = sig.strip()
        if not s:
            continue
        lang = _LANGS.get(s.lower())
        if lang:
            out.append((s, f"/search/repositories?q=language:{lang}"
                            f"+stars:>3&sort=updated&per_page=12"))
        else:
            term = s.replace(" ", "+")
            out.append((s, f"/search/repositories?q={term}"
                            f"+in:name,description,topics&sort=stars&per_page=12"))
    return out


def search_pool(pool, *, limit: int = 12, client=None, get=None) -> list[Candidate]:
    """Find people who have built what this pool is about."""
    get = get or (lambda p: _get(p, client))
    found: dict[str, Candidate] = {}

    for signal, q in queries(pool):
        try:
            items = get(q).get("items", []) or []
        except FindError:
            continue
        for repo in items:
            owner = (repo.get("owner") or {})
            login = owner.get("login")
            if not login or owner.get("type") != "User":
                continue
            c = found.setdefault(login, Candidate(
                login=login, url=owner.get("html_url", f"https://github.com/{login}")))
            c.matched.append(signal)
            ev = f"{repo.get('full_name')} ({repo.get('stargazers_count', 0)} stars)"
            if ev not in c.evidence:
                c.evidence.append(ev)

    ranked = sorted(found.values(), key=lambda c: (-c.score, -len(c.evidence)))[:limit]

    for c in ranked:                     # hydrate only the ones we will show
        try:
            u = get(f"/users/{c.login}")
        except FindError:
            continue
        c.name, c.location = u.get("name"), u.get("location")
        c.company, c.bio = u.get("company"), u.get("bio")
        c.public_repos = u.get("public_repos", 0)
        c.followers = u.get("followers", 0)
    return ranked


def render(pool, candidates: list[Candidate]) -> str:
    out = [f"{pool.name}  —  {len(candidates)} people who have built this", ""]
    if not candidates:
        out.append("  (no public repositories matched this pool's signals)")
    for i, c in enumerate(candidates, 1):
        who = c.name or c.login
        where = " · ".join(x for x in (c.location, c.company) if x)
        out.append(f"{i:2}. {who}  ({c.url})")
        if where:
            out.append(f"    {where}")
        if c.bio:
            out.append(f"    \"{c.bio.strip()}\"")
        out.append(f"    signals: {', '.join(sorted(set(c.matched)))}")
        for e in c.evidence[:3]:
            out.append(f"    built: {e}")
        out.append("")
    return "\n".join(out)


__all__ = ["Candidate", "FindError", "queries", "render", "search_pool"]
