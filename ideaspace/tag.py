"""Describe what each paper does, in field-neutral words, using Claude. This step is optional: without it the map still works from the text embeddings alone.
Needs ANTHROPIC_API_KEY. Results are cached in workspace/facets.jsonl so a rerun only tags new papers."""
import json, os, re
from pathlib import Path
import yaml

DEFAULT_MODEL = "claude-haiku-5-5"
DIMS = re.compile(r"^(?:[MLTKIN](?:\^-?\d+)?)(?: [MLTKIN](?:\^-?\d+)?)*$|^1$")


def vocab(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def prompt(batch, v):
    ops = "\n".join(f"- {k}: {d}" for k, d in v["operations"].items())
    evs = "\n".join(f"- {k}: {d}" for k, d in v["evidence_kinds"].items())
    units = "\n\n".join(f"[{i}] TITLE: {p['title']}\nABSTRACT: {(p.get('abstract') or '(none)')[:1800]}" for i, p in enumerate(batch))
    return f"""You tag research papers so that papers from different fields that do structurally similar things can be found next to each other. You describe what each paper says from its title and abstract only, without outside knowledge and without judging whether it is true.

For each paper return an object with:
- "core": one sentence stating the structure of the main finding or claim in words that avoid the field's jargon (what is held, changed, limited or recorded, by what, at what scale).
- "ops": 1 to 3 operations from this list:
{ops}
- "ev": one evidence kind from this list:
{evs}
- "dims": the base dimensions of the main quantities it tracks, each written like "M L^2 T^-2" (tokens M L T K I N, exponents with ^) or "1" for dimensionless; empty list if none.
- "scales": each length, duration, energy, rate, temperature or count it states, as printed (for example "77 K", "8-14 Hz"); empty list if none.
- "forms": named laws, equations or theorems it uses, by standard name; empty list if none.
- "disc": the field it would conventionally be filed under, as a short snake_case label (for example neuroscience, condensed_matter_physics, philosophy_of_mind).
- "sys": the system studied, in a few words, or "".
- "conf": 1 if the text is garbled or too thin to tag, 2 normally, 3 if clear.
Every number must be copied as printed. Use empty lists when nothing applies.

Return only a JSON array with one object per paper, in order, each with an "i" field equal to the number in brackets.

PAPERS
{units}"""


def clean(o, v):
    ops = [x for x in (o.get("ops") or []) if x in v["operations"]][:3]
    ev = o.get("ev") if o.get("ev") in v["evidence_kinds"] else None
    dims = [d for d in (o.get("dims") or []) if isinstance(d, str) and DIMS.match(d.strip())]
    lst = lambda k: [str(x)[:80] for x in (o.get(k) or []) if x][:6]
    return {"core": str(o.get("core") or "")[:400], "ops": ops, "ev": ev, "dims": dims, "scales": lst("scales"), "forms": lst("forms"),
            "disc": re.sub(r"[^a-z0-9_]+", "_", str(o.get("disc") or "").lower()).strip("_") or None, "sys": str(o.get("sys") or "")[:120], "conf": int(o.get("conf") or 2)}


def tag(papers, out_file, vocab_file, model=DEFAULT_MODEL, batch=8):
    import anthropic
    client = anthropic.Anthropic()
    v = vocab(vocab_file)
    done = {}
    if Path(out_file).exists():
        for l in open(out_file, encoding="utf-8"):
            r = json.loads(l)
            done[r["id"]] = r
    todo = [p for p in papers if p["id"] not in done]
    print(f"tagging {len(todo)} papers ({len(done)} already done)")
    with open(out_file, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), batch):
            b = todo[i:i + batch]
            msg = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt(b, v)}])
            txt = "".join(c.text for c in msg.content if getattr(c, "type", "") == "text")
            m = re.search(r"\[[\s\S]*\]", txt)
            try:
                arr = json.loads(m.group(0)) if m else []
            except Exception:
                arr = []
            got = {o.get("i"): o for o in arr if isinstance(o, dict)}
            for j, p in enumerate(b):
                if j in got:
                    rec = clean(got[j], v)
                    rec["id"] = p["id"]
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  {min(i + batch, len(todo))}/{len(todo)}", flush=True)
