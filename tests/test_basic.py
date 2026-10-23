import json, sys, types
from pathlib import Path
import numpy as np
from ideaspace import ingest, tag, layout

ROOT = Path(__file__).resolve().parents[1]


def test_doi_and_arxiv_normalisation():
    assert ingest.norm_doi("https://doi.org/10.1103/RevModPhys.75.715") == "10.1103/revmodphys.75.715"
    assert ingest.norm_doi("arXiv:1706.03762v5") == "10.48550/arxiv.1706.03762"
    assert ingest.norm_doi("no doi here") == ""


def test_txt_and_csv_readers(tmp_path):
    t = tmp_path / "a.txt"
    t.write_text("# comment\n10.1000/abc *\n10.1000/def  # note\n")
    recs = ingest.read_txt(t)
    assert [r["mine"] for r in recs] == [True, False]
    c = tmp_path / "a.csv"
    c.write_text("title,abstract,year,doi,authors,mine\nA paper,Some abstract,2020,10.1/x,A. One; B. Two,yes\n")
    r = ingest.read_csv(c)[0]
    assert r["mine"] and r["year"] == 2020 and r["authors"] == ["A. One", "B. Two"]


def test_bibtex_reader(tmp_path):
    b = tmp_path / "a.bib"
    b.write_text("@article{k,\n title = {A {Title}},\n author = {Doe, J. and Roe, R.},\n year = {2019},\n doi = {10.1000/y},\n journal = {J}\n}\n")
    r = ingest.read_bib(b)[0]
    assert r["title"] == "A Title" and r["year"] == 2019 and r["doi"] == "10.1000/y"


def test_tag_clean_keeps_only_allowed_values():
    v = tag.vocab(ROOT / "vocab.yaml")
    o = tag.clean({"core": "x", "ops": ["hold_alternatives", "bogus"], "ev": "nonsense", "dims": ["M L^2 T^-1", "kg"], "disc": "Quantum Biology", "conf": 3}, v)
    assert o["ops"] == ["hold_alternatives"] and o["ev"] is None and o["dims"] == ["M L^2 T^-1"] and o["disc"] == "quantum_biology"


def test_tag_with_a_stubbed_client(tmp_path, monkeypatch):
    class Msg:
        content = [types.SimpleNamespace(type="text", text=json.dumps([{"i": 0, "core": "c", "ops": ["gate_switch"], "ev": "theory_or_derivation", "dims": [], "scales": [], "forms": [], "disc": "physics", "sys": "", "conf": 2}]))]
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda: types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **k: Msg()))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    out = tmp_path / "f.jsonl"
    tag.tag([{"id": "t:1", "title": "T", "abstract": "A"}], out, ROOT / "vocab.yaml")
    assert json.loads(out.read_text())["ops"] == ["gate_switch"]
    tag.tag([{"id": "t:1", "title": "T", "abstract": "A"}], out, ROOT / "vocab.yaml")  # cached: nothing is appended
    assert len(out.read_text().splitlines()) == 1


def test_layout_shapes():
    rng = np.random.default_rng(0)
    P = rng.normal(size=(40, 16)).astype("float32")
    P /= np.linalg.norm(P, axis=1, keepdims=True)
    pos, r, order = layout.layout(P)
    assert pos.shape == (40, 3) and r.shape == (40,) and order.shape == (40, 12)
