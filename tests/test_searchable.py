"""A signal must be something you can type into a search box.

From a live playtest: an Aerospace Flight Simulation pool listed

    "Real-Time Digital Audio"

as a signal. That is the pool's topic restated, not a term that narrows
anything - searching it returns the same universe the pool already
describes. The contract asks for product and technology names; this
enforces it instead of hoping.
"""

from src.marketmap.searchable import is_searchable, keep


def test_the_live_failure_is_rejected():
    assert not is_searchable("Real-Time Digital Audio")


def test_a_plain_product_name_survives():
    assert is_searchable("Houdini")


def test_internal_capitals_are_a_name_shape():
    assert is_searchable("OpenUSD")


def test_digits_are_a_name_shape():
    assert is_searchable("ROS2")


def test_symbols_are_a_name_shape():
    for s in ("C++", "C#", ".NET"):
        assert is_searchable(s), s


def test_an_all_caps_acronym_survives_even_at_three_words():
    assert is_searchable("ARINC 653 partitioning")


def test_a_standard_name_survives_even_when_the_words_are_ordinary():
    assert is_searchable("Unreal Engine")


def test_a_two_word_discipline_term_survives():
    # Not a product, but a recruiter genuinely types it and it narrows.
    assert is_searchable("Project Controls")


def test_a_long_descriptor_phrase_is_rejected():
    assert not is_searchable("Python/C++ tooling and pipeline development")


def test_a_two_word_pure_category_is_rejected():
    assert not is_searchable("Systems Engineering")


def test_blank_entries_are_rejected():
    for s in ("", "   ", None):
        assert not is_searchable(s)


def test_keep_filters_a_list_and_reports_what_went():
    kept, dropped = keep(["Houdini", "Real-Time Digital Audio", "OpenUSD"])
    assert kept == ["Houdini", "OpenUSD"]
    assert dropped == ["Real-Time Digital Audio"]


def test_keep_never_empties_a_pool_that_had_only_prose():
    # Losing every signal is worse than showing weak ones; the reader can
    # judge a weak term, but cannot judge one they never saw.
    kept, dropped = keep(["Real-Time Digital Audio", "Systems Engineering"])
    assert kept == ["Real-Time Digital Audio", "Systems Engineering"]
    assert dropped == []
