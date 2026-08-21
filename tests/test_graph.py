import json

from src.marketmap.engine import generate
from src.marketmap.graph import render, write

BODY = {"core_shape": "building believable real-time systems under limits",
        "pools": [
          {"name": "Real-time VFX and virtual production", "transfer_logic": "same real-time work",
           "companies": ["ILMxLAB", "Weta FX"], "titles": ["Pipeline TD"],
           "signals": ["Houdini"], "tells": ["offline rendering"],
           "obviousness": 1, "confidence": 0.8},
          {"name": "Obvious pool", "transfer_logic": "the same job elsewhere",
           "titles": ["Simulation Engineer"], "obviousness": 5, "confidence": 0.9}]}


def a_map():
    return generate("Senior Simulation Engineer", "x" * 60,
                    complete=lambda p, *, system=None, **k: json.dumps(BODY))


def test_renders_a_complete_page():
    h = render(a_map())
    assert h.lstrip().startswith("<title>")
    assert "</script>" in h
    assert "const POOLS" in h


def test_page_is_self_contained():
    h = render(a_map())
    # Google Fonts is the only permitted remote host; nothing else may be fetched.
    for bad in ("cdn.", "unpkg", "jsdelivr", "src=\"http"):
        assert bad not in h, bad


def test_injects_the_real_map_not_a_fixture():
    h = render(a_map())
    assert "ILMxLAB" in h and "Weta FX" in h
    assert "Senior Simulation Engineer" in h
    assert "building believable real-time systems" in h


def test_defaults_to_the_non_obvious_pools():
    h = render(a_map())
    assert "Real-time VFX" in h
    assert '"Obvious pool"' not in h


def test_show_all_includes_them():
    h = render(a_map(), show_all=True)
    assert "Obvious pool" in h


def test_xray_string_is_embedded():
    h = render(a_map())
    assert "site:linkedin.com/in" in h


def test_long_pool_names_wrap_to_two_lines():
    h = render(a_map())
    assert "\\n" in h  # the wrapped name carries a newline into the JSON


def test_title_is_escaped():
    m = a_map()
    m.role_title = 'Engineer <script>alert(1)</script>'
    h = render(m)
    assert "<script>alert(1)</script>" not in h.split("const ROLE_TITLE")[0]


def test_write_creates_the_file(tmp_path):
    p = write(a_map(), tmp_path / "sub" / "map.html")
    assert p.exists() and p.read_text().startswith("<title>")


def test_no_placeholders_survive():
    h = render(a_map())
    for t in ("__TITLE__", "__ROLE__", "__POOLCOUNT__", "__MAP_DATA__"):
        assert t not in h
