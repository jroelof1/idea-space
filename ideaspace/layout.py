"""Hub-corrected distances, the 3D layout, and clusters named by their distinctive words."""
import collections, math, re
import numpy as np

K = 10
STOP = set("the of and in to a an for with on by from as at is are be this that these those we our their its it or not can may which has have been using use used based study studies paper results show shows shown between within into than more also such both two one new via per et al approach analysis model models system systems effect effects data method methods would could should among over under about while there where when what whose first second third other another each some most many much".split())


def spread_layout(emb, d0=3.6, iters=70, gap=1.22):
    """Pull cluster centres slightly apart, then relax the points so that no two sit closer than d0."""
    from scipy.spatial import cKDTree
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=max(2, min(36, len(emb) // 3)), n_init=3, random_state=3).fit(emb)
    cen = km.cluster_centers_[km.labels_]
    emb = (emb - cen) + (cen - emb.mean(0)) * gap + emb.mean(0)
    home, x = emb.copy(), emb.copy()
    for _ in range(iters):
        pairs = np.array(list(cKDTree(x).query_pairs(d0)))
        if len(pairs) == 0:
            break
        a, b = pairs[:, 0], pairs[:, 1]
        dv = x[a] - x[b]
        dd = np.linalg.norm(dv, axis=1, keepdims=True)
        dd[dd < 1e-6] = 1e-6
        push = dv / dd * (d0 - dd) * 0.3
        np.add.at(x, a, push)
        np.add.at(x, b, -push)
        x += (home - x) * 0.02
    return x - x.mean(0)


def layout(P, seed=7):
    """P is an (n, d) matrix of unit vectors. Returns 3D positions, mean distance to the 10 nearest (r), and the 12 nearest neighbours of each paper after hub correction."""
    import umap
    n = len(P)
    Dm = 1.0 - P @ P.T
    np.fill_diagonal(Dm, np.inf)
    k = min(K, n - 1)
    r = np.sort(Dm, axis=1)[:, :k].mean(axis=1)
    Dc = 2 * Dm - r[:, None] - r[None, :]
    Dc[np.isinf(Dm)] = np.inf
    Dc = Dc - np.min(Dc[np.isfinite(Dc)])
    np.fill_diagonal(Dc, 0.0)
    order = np.argsort(Dc + np.where(np.eye(n, dtype=bool), np.inf, 0), axis=1)[:, :min(12, n - 1)]
    emb = umap.UMAP(n_components=3, n_neighbors=min(15, n - 1), min_dist=0.8, spread=2.5, metric="precomputed", random_state=seed).fit_transform(Dc)
    emb = emb - emb.mean(0)
    emb = emb / np.abs(emb).max() * 100
    return spread_layout(emb), r, order


def cluster(P, papers, k):
    from sklearn.cluster import AgglomerativeClustering
    n = len(papers)
    lab = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(P)
    docs = [re.findall(r"[a-z]{4,}", (p["title"] + " " + (p.get("abstract") or "")[:300]).lower()) for p in papers]
    df = collections.Counter(w for t in docs for w in set(t))
    out = []
    for c in range(k):
        ix = [i for i in range(n) if lab[i] == c]
        tf = collections.Counter(w for i in ix for w in docs[i] if w not in STOP and len(w) >= 5)
        sc = {w: m * math.log(n / (1 + df[w])) for w, m in tf.items() if m >= 2}
        top = [w for w, _ in sorted(sc.items(), key=lambda kv: -kv[1])[:3]]
        discs = collections.Counter(papers[i]["facet"]["disc"] for i in ix if papers[i].get("facet") and papers[i]["facet"].get("disc"))
        ent = -sum((m / sum(discs.values())) * math.log2(m / sum(discs.values())) for m in discs.values()) if discs else 0.0
        ops = collections.Counter(o for i in ix if papers[i].get("facet") for o in papers[i]["facet"]["ops"])
        yrs = sorted(papers[i]["year"] for i in ix if papers[i].get("year"))
        out.append({"id": c, "name": " / ".join(top) if top else f"cluster {c}", "size": len(ix), "own": sum(1 for i in ix if papers[i]["kind"] == "ours"), "median_year": yrs[len(yrs) // 2] if yrs else None,
                    "top_ops": [o for o, _ in ops.most_common(3)], "field_mix_bits": round(ent, 2), "n_with_facets": int(sum(discs.values()))})
    return lab, out
