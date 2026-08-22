from src.marketmap.engine import generate
from src.marketmap.store import find, load, save, slug
import json

# Two pools, because obviousness is now a ranking and a lone pool cannot be
# ranked against anything - so a one-pool map has no non-obvious pool by
# construction, which would make this round-trip prove nothing.
BODY = {"core_shape": "s", "pools": [
    {"name": "p", "transfer_logic": "l", "companies": ["Rockstar"],
     "titles": ["Pipeline Technical Director"], "obviousness": 1},
    {"name": "q", "transfer_logic": "l", "companies": ["Ubisoft"],
     "titles": ["Simulation Engineer"], "obviousness": 5}]}


def test_round_trips(tmp_path):
    m = generate("Simulation Engineer", "x"*50,
                 complete=lambda p,*,system=None,**k: json.dumps(BODY))
    path = save(m, tmp_path)
    back = load(path)
    assert back.role_title == "Simulation Engineer"
    assert back.pools[0].companies == ["Rockstar"]
    assert back.non_obvious


def test_find_returns_none_when_absent(tmp_path):
    assert find("nothing here", tmp_path) is None


def test_slug_is_filesystem_safe():
    assert slug("Sr. Engineer, Simulation / AV") == "sr-engineer-simulation-av"
