"""Obviousness is a ranking, not a measurement.

The absolute 1-5 score shipped and collapsed: every pool in a payments map
scored 1/5, every pool in a pharmacist map scored 4/5, and the "hide the
obvious ones" toggle hid everything or nothing. The cause was that the score
measured whether the role title's distinctive noun happened to be a word
people put in job titles - "pharmacist" recurs everywhere, "payments" nowhere,
because those people say ledger and settlement and billing.

Two candidate absolute scorers were tried against every case we have evidence
for. Each fixed the reported failures and introduced a new false-high, and both
new failures were the same thing: a generic process word colliding across
domains. "Model Validation Lead" against "AV validation". "Quality & Compliance
Manager" against "regulatory compliance". Same word, different sense; no stop
list separates senses.

What the evidence does support is ORDER. Ranking held in all four multi-pool
maps, including both where banding failed. So the tests below assert order,
which is the claim the mechanism can actually make, and the UI says the score
is relative to this map rather than to the whole market.
"""

import pytest

from src.marketmap.closeness import UNRANKED, closeness, rank

AV = ("Senior Simulation Engineer, Autonomous Vehicles",
      "Build the simulation stack for AV validation: scenario generation, sensor "
      "models, replay of logged fleet data, closing the loop on vehicle behaviour.")
PAY = ("Staff Engineer, Payments",
       "Own the double-entry ledger recording every movement of money. Idempotency "
       "and reconciliation for payment flows that must balance to the cent across "
       "retries, partial failures and third-party processor outages.")
DON = ("Director of Nursing",
       "Lead clinical operations for a 200-bed skilled nursing facility. Survey "
       "readiness and regulatory compliance, nurse staffing ratios across three "
       "shifts, infection control, retention of an RN and CNA workforce.")
RX = ("Licensed Pharmacist, Retail",
      "Fill and verify prescriptions in a high-volume retail pharmacy. Counsel "
      "patients, administer immunisations, manage controlled substance records, "
      "supervise technicians. Active pharmacist licence and PharmD required.")

# (role, [(titles, "near"|"far")]) - every map that has ever failed.
MAPS = [
    (PAY, [(["Ledger Systems Architect", "General Ledger Engineer",
             "Core Banking Platform Developer"], "near"),
           (["Revenue Integrity Engineer", "Fare Reconciliation Developer",
             "Ticketing Systems Architect"], "far"),
           (["Billing Systems Engineer", "Rating Engine Developer",
             "Mediation Systems Analyst"], "far")]),
    (DON, [(["Director of Clinical Operations", "Regional Clinical Director",
             "VP of Clinical Services"], "near"),
           (["Regional Operations Manager", "District Manager",
             "Quality & Compliance Manager"], "far"),
           (["Store Operations Manager", "Logistics Center Manager",
             "Workforce Planning Manager"], "far")]),
    (AV, [(["Simulation Developer", "Simulation Specialist"], "near"),
          (["Quantitative Risk Analyst", "Model Validation Lead"], "far")]),
    (RX, [(["Staff Pharmacist", "Pharmacy Manager", "Clinical Pharmacist"], "near"),
          (["Automation Engineer", "Robotics Integration Specialist"], "far")]),
]


@pytest.mark.parametrize("role,pools", MAPS, ids=lambda v: v[0][:24] if isinstance(v, tuple) else "")
def test_the_near_pool_outranks_every_far_pool(role, pools):
    title, text = role
    scores = rank(title, text, [t for t, _ in pools])
    near = [s for s, (_, kind) in zip(scores, pools) if kind == "near"]
    far = [s for s, (_, kind) in zip(scores, pools) if kind == "far"]
    assert min(near) > max(far), f"near={near} far={far}"


@pytest.mark.parametrize("role,pools", MAPS, ids=lambda v: v[0][:24] if isinstance(v, tuple) else "")
def test_every_map_discriminates(role, pools):
    """The failure that started this: whole maps coming back all one number."""
    title, text = role
    assert len(set(rank(title, text, [t for t, _ in pools]))) > 1


def test_the_closest_pool_tops_the_scale_and_the_furthest_bottoms_it():
    title, text = PAY
    scores = rank(title, text, [["Ledger Systems Architect", "General Ledger Engineer"],
                                ["Revenue Integrity Engineer"],
                                ["Rating Engine Developer"]])
    assert max(scores) == 5 and min(scores) == 1


def test_a_lone_pool_cannot_be_ranked():
    assert rank(*PAY, [["Ledger Systems Architect"]]) == [UNRANKED]


def test_pools_that_tie_share_a_number():
    title, text = PAY
    s = rank(title, text, [["Ledger Systems Architect"], ["Ledger Systems Architect"]])
    assert s[0] == s[1]


def test_a_map_with_nothing_to_separate_claims_nothing():
    """All pools equally distant is not the same as all pools obvious."""
    title, text = PAY
    assert rank(title, text, [["Zebra Handler"], ["Kite Folder"]]) == [UNRANKED, UNRANKED]


def test_closeness_is_a_fraction_and_survives_junk():
    for titles in ([], [""], None, ["Ledger Systems Architect"]):
        v = closeness(*PAY, titles)
        assert 0.0 <= v <= 1.0


def test_scores_stay_inside_the_scale():
    title, text = DON
    for s in rank(title, text, [["A Manager"], ["Clinical Director"], ["Zebra Handler"]]):
        assert 1 <= s <= 5
