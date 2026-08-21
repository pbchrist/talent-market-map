import pytest

from src.marketmap.find import Candidate, FindError, queries, render, search_pool
from src.marketmap.types import Pool

POOL = Pool(name="Real-time VFX", transfer_logic="same work",
            companies=["Weta FX"], titles=["Pipeline TD"],
            signals=["Houdini", "C++", "OpenUSD"], tells=["offline rendering"])


def fake_api(repos_by_query, users=None):
    users = users or {}
    def _get(path):
        if path.startswith("/users/"):
            return users.get(path.split("/")[-1], {})
        for key, payload in repos_by_query.items():
            if key in path:
                return {"items": payload}
        return {"items": []}
    return _get


def repo(full, login, stars=10, typ="User"):
    return {"full_name": full, "stargazers_count": stars,
            "owner": {"login": login, "type": typ,
                      "html_url": f"https://github.com/{login}"}}


def test_languages_become_language_qualifiers():
    qs = dict((s, q) for s, q in queries(POOL))
    assert "language:C%2B%2B" in qs["C++"]
    assert "language:" not in qs["Houdini"]


def test_non_language_signals_search_name_description_topics():
    qs = dict((s, q) for s, q in queries(POOL))
    assert "in:name,description,topics" in qs["Houdini"]


def test_finds_people_who_built_the_thing():
    get = fake_api({"Houdini": [repo("ada/houdini-tools", "ada")]})
    out = search_pool(POOL, get=get)
    assert [c.login for c in out] == ["ada"]
    assert out[0].evidence == ["ada/houdini-tools (10 stars)"]


def test_ranks_by_distinct_signals_matched():
    get = fake_api({
        "Houdini": [repo("ada/h", "ada"), repo("bob/h", "bob")],
        "language:C%2B%2B": [repo("ada/engine", "ada")],
    })
    out = search_pool(POOL, get=get)
    assert out[0].login == "ada" and out[0].score == 2
    assert out[1].login == "bob" and out[1].score == 1


def test_skips_organizations():
    get = fake_api({"Houdini": [repo("weta/tools", "weta", typ="Organization")]})
    assert search_pool(POOL, get=get) == []


def test_hydrates_only_the_returned_candidates():
    calls = []
    base = fake_api({"Houdini": [repo("ada/h", "ada")]},
                    users={"ada": {"name": "Ada L", "location": "Wellington",
                                   "bio": "graphics", "public_repos": 22}})
    def counting(path):
        calls.append(path)
        return base(path)
    out = search_pool(POOL, get=counting)
    assert out[0].name == "Ada L" and out[0].location == "Wellington"
    assert calls.count("/users/ada") == 1


def test_a_failing_query_does_not_sink_the_search():
    def get(path):
        if "Houdini" in path:
            raise FindError("rate limited")
        if path.startswith("/users/"):
            return {}
        return {"items": [repo("bob/cpp", "bob")]}
    assert [c.login for c in search_pool(POOL, get=get)] == ["bob"]


def test_limit_is_respected():
    get = fake_api({"Houdini": [repo(f"u{i}/r", f"u{i}") for i in range(20)]})
    assert len(search_pool(POOL, get=get, limit=5)) == 5


def test_render_shows_evidence_not_just_names():
    c = Candidate(login="ada", url="https://github.com/ada", name="Ada L",
                  evidence=["ada/houdini-tools (10 stars)"], matched=["Houdini"])
    out = render(POOL, [c])
    assert "Ada L" in out and "built: ada/houdini-tools" in out


def test_render_says_so_when_nothing_matched():
    assert "no public repositories matched" in render(POOL, [])


from src.marketmap.find import tokenize


def test_tokenize_splits_parentheticals():
    assert tokenize("USD (OpenUSD)") == ["USD", "OpenUSD"]


def test_tokenize_splits_slashes_and_drops_filler():
    assert tokenize("Python/C++ tooling") == ["Python", "C++"]


def test_tokenize_handles_a_list_inside_parens():
    assert tokenize("crowd simulation (Golaem, Massive)") == [
        "crowd simulation", "Golaem", "Massive"]


def test_tokenize_leaves_a_clean_signal_alone():
    assert tokenize("real-time ray tracing") == ["real-time ray tracing"]


def test_tokenize_drops_bare_filler():
    assert tokenize("tooling") == []


def test_queries_expand_beyond_the_first_signal():
    p = Pool(name="x", transfer_logic="y",
             signals=["Python/C++ tooling", "USD (OpenUSD)"])
    got = [tok for tok, _ in queries(p)]
    assert "Python" in got and "C++" in got and "OpenUSD" in got
