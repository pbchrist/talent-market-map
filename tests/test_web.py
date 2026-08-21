import pytest

from src.marketmap.types import Pool
from src.marketmap.web import Hit, WebError, render, search, search_pool

POOL = Pool(name="Real-time VFX", transfer_logic="same work",
            companies=["Weta FX", "DNEG"], titles=["Pipeline TD"],
            signals=["Houdini", "OpenUSD"])

LI = "https://www.linkedin.com/in/ada-lovelace-1234"


def backend(hits):
    return lambda q, n, client: hits


def test_finds_linkedin_profiles():
    hits = [Hit("Ada Lovelace - Pipeline TD at Weta FX | LinkedIn", LI, "USD pipelines")]
    out = search_pool(POOL, backend=backend(hits))
    assert out[0].person == "Ada Lovelace"
    assert out[0].headline == "Pipeline TD at Weta FX"
    assert out[0].handle == "ada-lovelace-1234"


def test_drops_non_profile_results():
    hits = [Hit("Weta FX | LinkedIn", "https://www.linkedin.com/company/weta"),
            Hit("Ada - TD | LinkedIn", LI)]
    assert [h.handle for h in search_pool(POOL, backend=backend(hits))] == ["ada-lovelace-1234"]


def test_dedupes_the_same_person():
    hits = [Hit("Ada | LinkedIn", LI), Hit("Ada | LinkedIn", LI + "?trk=x")]
    assert len(search_pool(POOL, backend=backend(hits))) == 1


def test_runs_the_pools_xray_not_a_generic_query():
    seen = {}
    def spy(q, n, client):
        seen["q"] = q
        return []
    search_pool(POOL, backend=spy)
    assert seen["q"].startswith("site:linkedin.com/in")
    assert "Pipeline TD" in seen["q"] and "Weta FX" in seen["q"]


def test_site_is_swappable():
    seen = {}
    def spy(q, n, client):
        seen["q"] = q
        return []
    search_pool(POOL, site="github.com", backend=spy)
    assert seen["q"].startswith("site:github.com")


def test_works_with_no_keys_at_all(monkeypatch):
    from src.marketmap.web import available
    for k in ("BRAVE_API_KEY", "SERPER_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CSE_ID"):
        monkeypatch.delenv(k, raising=False)
    assert available() == "searx"


def test_a_key_takes_precedence_when_present(monkeypatch):
    from src.marketmap.web import available
    monkeypatch.setenv("BRAVE_API_KEY", "x")
    assert available() == "brave"


def test_headline_absent_is_not_fatal():
    assert search_pool(POOL, backend=backend([Hit("Ada Lovelace", LI)]))[0].headline == ""


def test_render_lists_people_with_links():
    hits = [Hit("Ada - TD at Weta | LinkedIn", LI, "OpenUSD tooling")]
    out = render(POOL, hits)
    assert "Ada" in out and LI in out and "OpenUSD tooling" in out


def test_render_says_so_when_empty():
    assert "nothing returned" in render(POOL, [])


def test_open_in_browser_builds_a_real_search_url(monkeypatch):
    from src.marketmap import web as W
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a[0]))
    urls = W.open_in_browser([POOL])
    assert urls[0].startswith("https://www.google.com/search?q=")
    assert "linkedin.com" in urls[0] and "Pipeline" in urls[0]
    assert calls and calls[0][0] == "open"


def test_open_in_browser_respects_the_site(monkeypatch):
    from src.marketmap import web as W
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)
    assert "github.com" in W.open_in_browser([POOL], site="github.com")[0]


def test_unknown_engine_is_refused(monkeypatch):
    from src.marketmap import web as W
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)
    with pytest.raises(WebError):
        W.open_in_browser([POOL], engine="askjeeves")
