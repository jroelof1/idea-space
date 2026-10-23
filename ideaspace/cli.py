import argparse, json, os, sys
from pathlib import Path


def cfg():
    p = Path("config.yaml")
    d = {}
    if p.exists():
        import yaml
        d = yaml.safe_load(p.read_text()) or {}
    return {"email": d.get("email") or os.environ.get("IDEASPACE_EMAIL", ""), "openalex_key": d.get("openalex_key") or os.environ.get("OPENALEX_API_KEY", ""),
            "model": d.get("tag_model") or os.environ.get("IDEASPACE_TAG_MODEL", "")}


def main():
    ap = argparse.ArgumentParser(prog="ideaspace", description="Build a 3D explorer for the ideas in your own papers.")
    ap.add_argument("-w", "--workspace", default="workspace", help="folder for everything this tool writes (default: workspace)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest", help="read a DOI list, CSV, JSONL, BibTeX file or a folder of PDFs into workspace/papers.jsonl")
    a.add_argument("source")
    a.add_argument("--mine-dir", default="mine", help="for a PDF folder: papers inside a subfolder with this name are marked as yours")
    a.add_argument("--add", action="store_true", help="add to the existing workspace instead of replacing it")
    t = sub.add_parser("tag", help="optional: describe what each paper does in field-neutral words (needs ANTHROPIC_API_KEY)")
    t.add_argument("--vocab", default=None)
    b = sub.add_parser("build", help="write workspace/idea_space.html")
    b.add_argument("--clusters", type=int, default=None)
    b.add_argument("-o", "--out", default=None)
    al = sub.add_parser("all", help="ingest, tag (if a key is set) and build in one go")
    al.add_argument("source")
    al.add_argument("--mine-dir", default="mine")
    args = ap.parse_args()
    ws = Path(args.workspace)
    ws.mkdir(parents=True, exist_ok=True)
    c = cfg()
    vocab_default = Path(__file__).resolve().parents[1] / "vocab.yaml"

    def do_ingest(src, mine_dir, add=False):
        from .ingest import ingest
        recs = ingest(src, c["email"], c["openalex_key"], mine_dir)
        f = ws / "papers.jsonl"
        if add and f.exists():
            old = [json.loads(l) for l in open(f, encoding="utf-8")]
            have = {r["id"] for r in old}
            recs = old + [r for r in recs if r["id"] not in have]
        f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
        print(f"{len(recs)} items in {f}; {sum(1 for r in recs if r['abstract'])} have abstracts, {sum(1 for r in recs if r['mine'])} are marked as yours")

    def do_tag(vocab):
        from .tag import tag, DEFAULT_MODEL
        papers = [json.loads(l) for l in open(ws / "papers.jsonl", encoding="utf-8")]
        tag(papers, ws / "facets.jsonl", vocab or vocab_default, c["model"] or DEFAULT_MODEL)

    def do_build(clusters=None, out=None):
        from .build import build
        build(ws, out, clusters)

    if args.cmd == "ingest":
        do_ingest(args.source, args.mine_dir, args.add)
    elif args.cmd == "tag":
        do_tag(args.vocab)
    elif args.cmd == "build":
        do_build(args.clusters, args.out)
    else:
        do_ingest(args.source, args.mine_dir)
        if os.environ.get("ANTHROPIC_API_KEY"):
            do_tag(None)
        else:
            print("ANTHROPIC_API_KEY is not set, so the tagging step is skipped. The map works without it; run `ideaspace tag` later to add structure tags.")
        do_build()
