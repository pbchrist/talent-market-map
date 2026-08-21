"""Search strings, built from the map rather than asked for.

The model's job is judgement: which pools, why they transfer, who is in
them. Turning that into syntax is mechanical, so it happens in code. A
model asked to emit boolean will quietly drop an OR, unbalance a paren,
or invent an operator LinkedIn does not have. This cannot.
"""

from src.marketmap.searchable import is_searchable


def _quote(term: str) -> str:
    term = term.strip().strip('"')
    return f'"{term}"' if " " in term else term


def _or_group(terms: list[str]) -> str:
    clean = [_quote(t) for t in dict.fromkeys(t for t in terms if t.strip())]
    if not clean:
        return ""
    return "(" + " OR ".join(clean) + ")" if len(clean) > 1 else clean[0]


def boolean(pool) -> str:
    """A LinkedIn-Recruiter-style boolean for one pool."""
    parts = [p for p in (_or_group(pool.titles), _or_group(pool.companies)) if p]
    return " AND ".join(parts)


def xray(pool, site: str = "linkedin.com/in") -> str:
    """A Google X-ray. Works without any seat, licence or database."""
    parts = [f"site:{site}"]
    for group in (_or_group(pool.titles), _or_group(pool.companies)):
        if group:
            parts.append(group)
    # Filtered again here, not just at intake. keep() lets prose through when
    # a pool has nothing better, so the reader can still see what the model
    # said - but a search string has no such need. An X-ray missing its signal
    # group is still a good search; one carrying "Real-Time Digital Audio" is
    # the failure this guards against.
    usable = [s for s in pool.signals if is_searchable(s)]
    if usable:
        parts.append(_or_group(usable[:4]))
    return " ".join(parts)


def github(pool) -> str:
    """GitHub search for the same pool, where the shape is code-shaped."""
    langs = [s for s in pool.signals if s.lower() in {
        "c++", "c#", "python", "rust", "go", "cuda", "glsl", "hlsl", "java"}]
    q = " ".join(_quote(t) for t in pool.titles[:2])
    if langs:
        q += " " + " ".join(f"language:{l}" for l in langs[:2])
    return q.strip()


def exclusions(pool) -> str:
    """Negative terms from the pool's own disqualifiers."""
    return " ".join(f"-{_quote(t)}" for t in pool.tells[:5])
