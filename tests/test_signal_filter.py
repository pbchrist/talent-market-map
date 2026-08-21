"""Signals reaching a pool have been through the searchability filter."""

import json

from src.marketmap.engine import generate

ROLE = ("Senior Simulation Engineer, Autonomous Vehicles",
        "Build the simulation stack for AV validation.")

RESPONSE = json.dumps({
    "core_shape": "Keeping a simulated world believable in real time.",
    "pools": [{
        "name": "Aerospace Flight Simulation",
        "transfer_logic": "They certified simulators against real aircraft.",
        "companies": ["CAE", "FlightSafety"],
        "titles": ["Simulation Systems Engineer"],
        "signals": ["Real-Time Digital Audio", "DO-178C", "Presagis"],
        "tells": ["Only operated simulators"],
        "obviousness": 2,
        "confidence": 0.7,
    }],
})


def _map():
    return generate(*ROLE, complete=lambda *a, **k: RESPONSE)


def test_the_unsearchable_signal_is_gone():
    assert "Real-Time Digital Audio" not in _map().pools[0].signals


def test_the_real_terms_survive():
    assert _map().pools[0].signals == ["DO-178C", "Presagis"]


def test_the_pool_records_what_was_dropped():
    assert _map().pools[0].dropped_signals == ["Real-Time Digital Audio"]
