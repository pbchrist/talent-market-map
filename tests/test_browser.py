import pytest

from src.marketmap.browser import BrowserError, Profile, render, search
from src.marketmap.types import Pool

POOL = Pool(name="Aviation training", transfer_logic="same work",
            companies=["CAE", "L3Harris"], titles=["Simulator Software Engineer"],
            signals=["STK"])


def test_parses_a_linkedin_result():
    p = Profile(url="https://www.linkedin.com/in/tshields1",
                title="Thomas Shields - Sr Engineer, Simulator Support at Delta | LinkedIn")
    assert p.handle == "tshields1"
    assert p.person == "Thomas Shields"
    assert p.headline == "Sr Engineer, Simulator Support at Delta"


def test_headline_optional():
    assert Profile(url="https://www.linkedin.com/in/x", title="Ada").headline == ""


def test_unknown_engine_refused():
    with pytest.raises(BrowserError):
        search("q", engine="askjeeves")


def test_render_lists_people():
    p = Profile(url="https://www.linkedin.com/in/tshields1",
                title="Thomas Shields - Sr Engineer | LinkedIn", snippet="simulators")
    out = render(POOL, [p])
    assert "Thomas Shields" in out and "tshields1" in out and "simulators" in out


def test_render_handles_nothing_found():
    assert "nothing returned" in render(POOL, [])


def test_search_pool_splits_into_narrow_queries(monkeypatch):
    from src.marketmap import browser as B
    seen = []
    monkeypatch.setattr(B, "search", lambda q, **k: seen.append(q) or [])
    B.search_pool(POOL, limit=5)
    assert all(len(q) < 120 for q in seen), "queries must stay narrow enough to return results"
    assert any('"Simulator Software Engineer"' in q and '"CAE"' in q for q in seen)
