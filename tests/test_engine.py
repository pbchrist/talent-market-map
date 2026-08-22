import json

import pytest

from src.marketmap.closeness import UNRANKED
from src.marketmap.engine import MapError, generate

BODY = {"core_shape": "building believable real-time systems under limits",
        "pools": [
          {"name": "Procedural generation", "transfer_logic": "same real-time systems work",
           "companies": ["Rockstar"], "titles": ["Technical Artist"],
           "signals": ["Houdini"], "tells": ["Student"], "obviousness": 1, "confidence": 0.9},
          {"name": "Obvious pool", "transfer_logic": "the same job elsewhere",
           "titles": ["Simulation Engineer"], "obviousness": 5, "confidence": 0.9}]}


def fake(payload):
    return lambda p, *, system=None, **k: (
        payload if isinstance(payload, str) else json.dumps(payload))


def test_builds_a_map():
    m = generate("Simulation Engineer", "x"*50, complete=fake(BODY))
    assert m.core_shape.startswith("building believable")
    assert len(m.pools) == 2


def test_non_obvious_filters_out_the_pools_everyone_searches():
    m = generate("Simulation Engineer", "x"*50, complete=fake(BODY))
    assert [p.name for p in m.non_obvious] == ["Procedural generation"]


def test_the_models_obviousness_is_ignored_entirely():
    # It rated quant risk 4/5 for an AV simulation req and military
    # construction 1/5 for a construction req. Wrong in both directions, so
    # the number is never the model's. See closeness.py.
    body = {"core_shape": "s", "pools": [
        {"name": "p", "transfer_logic": "l", "titles": ["Pipeline TD"],
         "obviousness": 5, "confidence": 5.0}]}
    p = generate("Simulation Engineer", "x"*50, complete=fake(body)).pools[0]
    # A lone pool has nothing to be nearer than, so the honest answer is "no
    # opinion" - which is emphatically not the 5 the model asked for.
    assert p.obviousness == UNRANKED
    assert p.confidence == 1.0         # confidence is still clamped


def test_a_synonym_pool_outranks_a_foreign_one():
    body = {"core_shape": "s", "pools": [
        {"name": "synonym", "transfer_logic": "l", "titles": ["Simulation Developer"]},
        {"name": "foreign", "transfer_logic": "l", "titles": ["Pipeline TD"]}]}
    pools = {p.name: p.obviousness for p in
             generate("Simulation Engineer", "x"*50, complete=fake(body)).pools}
    assert pools["synonym"] > pools["foreign"]


def test_drops_a_pool_with_no_transfer_logic():
    body = {"core_shape": "s", "pools": [
        {"name": "p", "transfer_logic": "  "},
        {"name": "q", "transfer_logic": "real"}]}
    assert [p.name for p in generate("t", "x"*50, complete=fake(body)).pools] == ["q"]


def test_raises_without_core_shape():
    with pytest.raises(MapError):
        generate("t", "x"*50, complete=fake({"pools": [{"name":"p","transfer_logic":"l"}]}))


def test_raises_when_no_pools_survive():
    with pytest.raises(MapError):
        generate("t", "x"*50, complete=fake({"core_shape": "s", "pools": []}))


def test_raises_on_non_json():
    with pytest.raises(MapError):
        generate("t", "x"*50, complete=fake("I cannot help with that"))
