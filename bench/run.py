"""Does this codebase still behave the way it did when it was known good?

Not a test suite. The tests say each piece is correct in isolation; this says
the whole pipeline still produces the SAME answers it produced on the day
everything worked. The obviousness regression that shipped and sat live for
hours would have shown up here on the first run.

The model is stubbed with a fixed response on purpose - we are benchmarking
this code, not Qwen.

    python bench/run.py             compare against the recorded baseline
    python bench/run.py --update    re-record (only when a change is INTENDED)
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import subprocess                                       # noqa: E402

from src.marketmap import strings                       # noqa: E402
from src.marketmap.engine import generate               # noqa: E402
from src.marketmap.closeness import rank                # noqa: E402
from src.marketmap.searchable import is_searchable      # noqa: E402

HERE = pathlib.Path(__file__).parent
BASELINE = HERE / "baseline.json"

ROLE_TITLE = "Staff Engineer, Payments"
ROLE_TEXT = ("Own the double-entry ledger that records every movement of money "
             "through the platform. Idempotency and reconciliation for payment "
             "flows that must balance to the cent across retries, partial "
             "failures and third-party processor outages.")

# Fixed response carrying one of each thing the gates handle: a near pool, a
# far pool, a pure synonym pool, and signals of both kinds.
RESPONSE = json.dumps({
    "core_shape": "Guaranteeing financial consistency across distributed failure.",
    "pools": [
        {"name": "Core Banking Ledger", "transfer_logic": "They built the general ledger.",
         "companies": ["Temenos", "Finastra"],
         "titles": ["Ledger Systems Architect", "General Ledger Engineer"],
         "signals": ["Temenos", "GL Reconciliation", "Real-Time Digital Audio"],
         "tells": ["Reporting only"], "obviousness": 3, "confidence": 0.8},
        {"name": "Airline Revenue Integrity", "transfer_logic": "They reconciled ticket sales.",
         "companies": ["Sabre", "Amadeus"],
         "titles": ["Revenue Integrity Engineer", "Fare Reconciliation Developer"],
         "signals": ["Sabre", "Systems Engineering"],
         "tells": ["Pricing only"], "obviousness": 1, "confidence": 0.6},
        {"name": "Payments Synonyms", "transfer_logic": "Same job, different words.",
         "companies": ["Stripe"], "titles": ["Payments Engineer", "Payments Platform Developer"],
         "signals": ["Houdini"], "tells": [], "obviousness": 1, "confidence": 0.5},
    ],
})

SEARCHABLE_CASES = [
    "Real-Time Digital Audio", "Houdini", "OpenUSD", "ROS2", "C++",
    "ARINC 653 partitioning", "Unreal Engine", "Project Controls",
    "Systems Engineering", "Python/C++ tooling and pipeline development",
]

PARITY = json.loads((HERE / "parity-cases.json").read_text())


def parity():
    """The deployed page runs its own copy of these gates. Once already, a fix
    landed in Python and never reached docs/app.js, and the live page stayed
    wrong for hours with every test green. This compares the two directly."""
    py = {
        "searchable": {s: is_searchable(s) for s in PARITY["searchable"]},
        "rank": {c["id"]: rank(c["role_title"], c["role_text"], c["pools"])
                 for c in PARITY["rank"]},
    }
    try:
        js = json.loads(subprocess.run(
            ["node", str(HERE / "parity.js")], capture_output=True, text=True,
            timeout=60, check=True).stdout)
    except Exception as exc:
        return [("node could not run", "-", str(exc)[:80])]
    return [(f"{sec}.{k}", v, js.get(sec, {}).get(k))
            for sec in py for k, v in py[sec].items()
            if v != js.get(sec, {}).get(k)]


def measure():
    m = generate(ROLE_TITLE, ROLE_TEXT, complete=lambda *a, **k: RESPONSE)
    return {
        "pipeline": {
            p.name: {
                "obviousness": p.obviousness,
                "signals": p.signals,
                "dropped_signals": p.dropped_signals,
                "xray": strings.xray(p),
                "boolean": strings.boolean(p),
            } for p in m.pools
        },
        "searchable": {s: is_searchable(s) for s in SEARCHABLE_CASES},
        "rank": {c["id"]: rank(c["role_title"], c["role_text"], c["pools"])
                 for c in PARITY["rank"]},
    }


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def main():
    now = measure()
    if "--update" in sys.argv or not BASELINE.exists():
        BASELINE.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n")
        print(f"baseline recorded: {BASELINE}")
        return 0
    was, isnow = flatten(json.loads(BASELINE.read_text())), flatten(now)
    diffs = [(k, was.get(k), isnow.get(k))
             for k in sorted(set(was) | set(isnow)) if was.get(k) != isnow.get(k)]
    drift = parity()
    if drift:
        print(f"talent-market-map   PYTHON AND JAVASCRIPT DISAGREE  ({len(drift)})\n")
        for k, a, b in drift:
            print(f"  {k}\n      python: {a}\n      js    : {b}")
        print("\nThe deployed page is the JavaScript. Fix docs/app.js.")
        return 1

    if not diffs:
        print(f"talent-market-map   SAME as known good  "
              f"({len(isnow)} checks, python and js agree)")
        return 0
    print(f"talent-market-map   CHANGED  ({len(diffs)} of {len(isnow)} checks differ)\n")
    for k, a, b in diffs:
        print(f"  {k}\n      was: {a}\n      now: {b}")
    print("\nIf every change above is one you meant to make:  python bench/run.py --update")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
