import json

from src.marketmap.cli import main

BODY = json.dumps({"core_shape": "shape", "pools": [
    {"name": "Real-time VFX", "transfer_logic": "same work",
     "companies": ["Weta FX"], "titles": ["Pipeline TD"], "obviousness": 1}]})


def test_graph_flag_writes_a_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("src.marketmap.llm.complete", lambda *a, **k: BODY)
    monkeypatch.setattr("src.marketmap.store.MAPS_DIR", tmp_path)
    out = tmp_path / "g.html"
    assert main(["--title", "Sim Engineer", "--role", "a job description here",
                 "--graph", str(out)]) == 0
    assert out.exists()
    assert "Weta FX" in out.read_text()


def test_no_graph_without_the_flag(tmp_path, monkeypatch):
    monkeypatch.setattr("src.marketmap.llm.complete", lambda *a, **k: BODY)
    monkeypatch.setattr("src.marketmap.store.MAPS_DIR", tmp_path)
    main(["--title", "Sim Engineer", "--role", "a job description here"])
    assert not list(tmp_path.glob("*.html"))
