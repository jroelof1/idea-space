"""Assemble the page data (vectors, layout, clusters, tags) and write one self-contained idea_space.html."""
import base64, json
from pathlib import Path
import numpy as np
from . import embed as emb_mod
from .layout import layout, cluster

HERE = Path(__file__).parent


def build(ws, out_html=None, n_clusters=None):
    ws = Path(ws)
    papers_in = [json.loads(l) for l in open(ws / "papers.jsonl", encoding="utf-8")]
    facets = {}
    if (ws / "facets.jsonl").exists():
        for l in open(ws / "facets.jsonl", encoding="utf-8"):
            r = json.loads(l)
            facets[r["id"]] = r
    n = len(papers_in)
    if n < 12:
        raise SystemExit(f"Only {n} items. Add at least 12 so the map has something to lay out.")
    papers = []
    for p in papers_in:
        f = facets.get(p["id"])
        facet = {"core": f["core"], "ops": f["ops"], "ev": f["ev"], "dims": f["dims"], "scales": f["scales"], "forms": f["forms"], "disc": f["disc"], "conf": f["conf"], "sys": f["sys"]} if f else None
        papers.append({"id": p["id"], "kind": "ours" if p.get("mine") else "cited", "title": p["title"][:230], "year": p.get("year"), "cites": p.get("cites") or 0, "authors": "", "au": ", ".join(p.get("authors") or [])[:300],
                       "ref": "", "venue": (p.get("venue") or "")[:80], "doi": p.get("doi"), "url": p.get("url"), "abstract": (p.get("abstract") or "")[:650], "has_abs": bool(p.get("abstract")), "n_uses": 0,
                       "docs": ["your collection"], "community": None, "fulltext": "not attempted", "status": "", "quotes": [], "n_quotes": 0, "n_passages": 0, "facet": facet, "follow": [], "why": [], "pos": {},
                       "relevance": None, "org": [], "brain": False})
    texts = [(p["title"] + ". " + (p.get("abstract") or ""))[:1500] for p in papers_in]
    P = emb_mod.embed(texts, ws / "cache")
    pos, r, order = layout(P)
    k = n_clusters or min(36, max(4, n // 12))
    lab, clusters = cluster(P, papers, k)
    for i, p in enumerate(papers):
        p["cluster"] = int(lab[i])
    # thin spots: midpoints of near pairs whose nearest paper is far relative to local spacing
    gaps, cand_g = [], []
    for i in range(n):
        for j in order[i][:10]:
            if j <= i and i in order[j][:10]:
                continue
            m = P[i] + P[j]
            m /= np.linalg.norm(m)
            near = float(1 - np.max(np.delete(P @ m, [i, int(j)])))
            cand_g.append((float(near / max(1e-6, (r[i] + r[j]) / 2)), int(i), int(j)))
    cand_g.sort(reverse=True)
    for ratio, i, j in cand_g:
        mid = (pos[i] + pos[j]) / 2
        if any(np.linalg.norm(mid - np.array(g["pos"])) < 9 for g in gaps):
            continue
        yi, yj = papers[i]["year"], papers[j]["year"]
        gaps.append({"pos": np.round(mid, 2).tolist(), "a": i, "b": j, "ratio": round(ratio, 2), "split": bool(yi and yj and abs(yi - yj) > 15)})
        if len(gaps) >= 40:
            break
    if not gaps:
        gaps = [{"pos": [0, 0, 0], "a": 0, "b": 1, "ratio": 1.0, "split": False}]
    sc8 = np.abs(P).max(axis=1) / 127.0
    q8 = np.round(P / sc8[:, None]).astype(np.int8)
    kinds = [p["kind"] for p in papers]
    out = {"profiles": {}, "papers": papers, "pos": np.round(pos, 2).tolist(), "nbrs": order.astype(int).tolist(), "r": np.round(r, 4).tolist(), "clusters": clusters, "cand": [], "gaps": gaps,
           "vec": base64.b64encode(q8.tobytes()).decode(), "vscale": base64.b64encode(sc8.astype(np.float32).tobytes()).decode(), "dim": int(P.shape[1]),
           "stats": {"n": n, "ours": kinds.count("ours"), "cited": kinds.count("cited"), "background": 0, "author": 0, "linked": 0, "quote": 0, "with_facets": sum(1 for p in papers if p["facet"])}}
    data = json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("�", "").replace("</", "<\\/")
    html = (HERE / "page" / "template.html").read_text(encoding="utf-8").replace("__DATA__", data)
    three = (HERE / "page" / "vendor" / "three.min.js").read_text(encoding="utf-8")  # bundled, so the file works without an internet connection
    tag = '<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>'
    html = html.replace(tag, "<script>" + three + "</script>")
    out_html = Path(out_html or ws / "idea_space.html")
    out_html.write_text(html, encoding="utf-8")
    print(f"wrote {out_html} ({out_html.stat().st_size // 1024} KB): {n} items, {len(clusters)} clusters, {out['stats']['with_facets']} tagged")
    return out_html
