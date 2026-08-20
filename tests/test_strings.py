from src.marketmap.strings import boolean, exclusions, github, xray
from src.marketmap.types import Pool

POOL = Pool(
    name="Procedural generation",
    transfer_logic="same real-time systems work",
    companies=["Rockstar Games", "Ubisoft"],
    titles=["Technical Artist", "Procedural Generation Engineer"],
    signals=["Houdini", "C++", "Unreal"],
    tells=["Recruiter", "Student"],
)


def test_boolean_groups_titles_and_companies():
    b = boolean(POOL)
    assert '"Technical Artist" OR "Procedural Generation Engineer"' in b
    assert " AND " in b
    assert b.count("(") == b.count(")")


def test_single_term_is_not_wrapped_in_a_group():
    assert boolean(Pool(name="x", transfer_logic="y", titles=["Engineer"])) == "Engineer"


def test_unspaced_terms_are_not_quoted():
    assert '"Houdini"' not in xray(POOL)


def test_xray_targets_linkedin_by_default():
    assert xray(POOL).startswith("site:linkedin.com/in")


def test_xray_is_balanced():
    x = xray(POOL)
    assert x.count("(") == x.count(")")


def test_github_picks_up_languages_as_qualifiers():
    assert "language:c++" in github(POOL).lower()


def test_exclusions_negate_the_tells():
    assert exclusions(POOL) == '-Recruiter -Student'


def test_empty_pool_produces_no_syntax_garbage():
    empty = Pool(name="x", transfer_logic="y")
    assert boolean(empty) == ""
    assert xray(empty) == "site:linkedin.com/in"


def test_duplicate_titles_collapse():
    p = Pool(name="x", transfer_logic="y", titles=["Engineer", "Engineer"])
    assert boolean(p).count("Engineer") == 1
