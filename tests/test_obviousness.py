"""Obviousness must be derived, not taken from the model.

Two live failures, opposite directions:

  Financial Risk Modeling scored 4/5 for an autonomous-vehicle simulation
  req. 5 means "every recruiter searches here first". No AV recruiter starts
  at quant risk.

  Military Construction scored 1/5 for a commercial construction PM req.
  USACE and NAVFAC are adjacent enough that a good construction recruiter
  would reach them; 1 means "almost nobody would think of this".

The model is treating "different industry vocabulary" as "nobody would think
of this", which is precisely the judgement it is worst at. Lexical distance
from the role's own title is a measurable proxy for it, and unlike the
model's guess it is stable across runs.
"""

from src.marketmap.obviousness import derive

AV = "Senior Simulation Engineer, Autonomous Vehicles"
CPM = "Commercial Construction Project Manager"


def test_quant_risk_is_exotic_for_an_av_simulation_req():
    assert derive(AV, ["Quantitative Risk Analyst", "Model Validation Lead"]) <= 2


def test_military_construction_is_not_exotic_for_a_construction_req():
    # shares the word "construction" with the role, so a construction
    # recruiter plausibly reaches it
    assert derive(CPM, ["Military Construction Manager", "Construction Engineer"]) >= 3


def test_a_title_synonym_is_maximally_obvious():
    assert derive(AV, ["Simulation Engineer", "Senior Simulation Developer"]) == 5


def test_completely_foreign_vocabulary_is_least_obvious():
    assert derive(AV, ["Pipeline TD", "Immersive Media Technical Director"]) == 1


def test_partial_overlap_lands_in_the_middle():
    v = derive(CPM, ["Project Controls Manager", "Capital Projects Lead"])
    assert 2 <= v <= 4


def test_stopwords_do_not_count_as_overlap():
    # "of", "the", "and" must not make a pool look obvious
    assert derive(CPM, ["Head of the Line and Yard"]) <= 2


def test_no_titles_is_treated_as_unknown_not_obvious():
    assert derive(AV, []) == 3


def test_result_is_always_in_range():
    for titles in ([], [""], ["x"], ["Simulation"] * 20):
        assert 1 <= derive(AV, titles) <= 5
