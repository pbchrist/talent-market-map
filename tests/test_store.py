from src.marketmap.engine import generate
from src.marketmap.store import find, load, save, slug
import json

BODY = {"core_shape": "s", "pools": [{"name": "p", "transfer_logic": "l",
        "companies": ["Rockstar"], "titles": ["TA"], "obviousness": 1}]}


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
