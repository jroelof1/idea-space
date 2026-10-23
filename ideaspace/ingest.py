"""Turn whatever you have (DOI list, CSV, JSONL, BibTeX, a folder of PDFs) into one normalised list of papers, filling in missing abstracts from OpenAlex."""
import csv, json, os, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>,;]+", re.I)
ARXIV_RE = re.compile(r"(?:arxiv[:/ ]|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
API = "https://api.openalex.org/works"


def _get(url, email, key):
    sep = "&" if "?" in url else "?"
    url += sep + "mailto=" + urllib.parse.quote(email or "you@example.org")
    if key:
        url += "&api_key=" + key
    err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ideaspace"}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429 and not key:
                raise SystemExit("OpenAlex refused the request because no API key was given. Get a free key at https://openalex.org/settings/api and put it in config.yaml (openalex_key) or the OPENALEX_API_KEY environment variable.")
            if e.code < 500 and e.code != 429:
                break
        except Exception as e:
            err = e
        time.sleep(2 * (attempt + 1))
    print("warning: OpenAlex request failed:", err)
    return None


def abstract_of(w):
    ii = w.get("abstract_inverted_index")
    if not ii:
        return ""
    pos = sorted((p, t) for t, ps in ii.items() for p in ps)
    return " ".join(t for _, t in pos)


def norm_doi(s):
    s = (s or "").strip()
    m = ARXIV_RE.search(s)
    if m:
        return "10.48550/arxiv." + m.group(1)
    m = DOI_RE.search(s)
    return m.group(0).rstrip(".)").lower() if m else ""


def _from_oa(w):
    venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    return {"title": w.get("title") or "", "year": w.get("publication_year"), "doi": norm_doi(w.get("doi") or ""), "authors": [a["author"]["display_name"] for a in w.get("authorships", [])],
            "venue": venue, "abstract": abstract_of(w), "cites": w.get("cited_by_count") or 0, "url": w.get("id")}


def resolve(recs, email, key):
    """Fill title, abstract, year, authors and venue for records that have a DOI but lack them."""
    need = [r for r in recs if r.get("doi") and (not r.get("abstract") or not r.get("title"))]
    for i in range(0, len(need), 40):
        chunk = need[i:i + 40]
        flt = "|".join("https://doi.org/" + r["doi"] for r in chunk)
        res = _get(f"{API}?filter=doi:{urllib.parse.quote(flt, safe=':/|')}&per-page=50", email, key)
        by = {norm_doi(w.get("doi") or ""): w for w in (res or {}).get("results", [])}
        for r in chunk:
            w = by.get(r["doi"])
            if w:
                for k, v in _from_oa(w).items():
                    if v and not r.get(k):
                        r[k] = v
    return recs


def search_title(title, email, key):
    res = _get(f"{API}?search={urllib.parse.quote(title[:200])}&per-page=3", email, key)
    ws = (res or {}).get("results") or []
    return _from_oa(ws[0]) if ws else None


def read_txt(p):
    """One DOI, DOI URL or arXiv id per line. End a line with * (or the word mine) to mark it as one of your own papers."""
    out = []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            d = norm_doi(line)
            if d:
                out.append({"doi": d, "mine": line.endswith("*") or line.lower().endswith(" mine")})
    return out


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        out.append({"title": r.get("title", ""), "abstract": r.get("abstract", ""), "year": int(r["year"]) if r.get("year", "").isdigit() else None, "doi": norm_doi(r.get("doi", "")),
                    "authors": [a.strip() for a in re.split(r";|\band\b", r.get("authors", "")) if a.strip()], "venue": r.get("venue", ""), "url": r.get("url", ""),
                    "mine": r.get("mine", "").lower() in ("1", "true", "yes", "y", "x")})
    return out


def read_jsonl(p):
    txt = Path(p).read_text(encoding="utf-8").strip()
    rows = json.loads(txt) if txt.startswith("[") else [json.loads(l) for l in txt.splitlines() if l.strip()]
    for r in rows:
        r["doi"] = norm_doi(r.get("doi", ""))
        if isinstance(r.get("authors"), str):
            r["authors"] = [a.strip() for a in re.split(r";|\band\b", r["authors"]) if a.strip()]
    return rows


def _bib_field(entry, key):
    m = re.search(r"\b" + key + r"\s*=\s*", entry, re.I)
    if not m:
        return ""
    i = m.end()
    if i >= len(entry):
        return ""
    if entry[i] == "{":
        depth, j = 0, i
        while j < len(entry):
            depth += entry[j] == "{"
            depth -= entry[j] == "}"
            if depth == 0:
                break
            j += 1
        return entry[i + 1:j]
    if entry[i] == '"':
        j = entry.find('"', i + 1)
        return entry[i + 1:j if j > 0 else len(entry)]
    j = re.search(r"[,\n}]", entry[i:])
    return entry[i:i + (j.start() if j else 0)].strip()


def read_bib(p):
    out = []
    for m in re.finditer(r"@\w+\s*\{[^@]*?(?=\n@|\Z)", Path(p).read_text(encoding="utf-8"), re.S):
        e = m.group(0)
        fld = lambda k: _bib_field(e, k)
        y = fld("year")
        out.append({"title": re.sub(r"[{}]", "", fld("title")).strip(), "abstract": re.sub(r"[{}]", "", fld("abstract")).strip(), "year": int(y) if y.isdigit() else None, "doi": norm_doi(fld("doi")),
                    "authors": [a.strip() for a in re.split(r"\sand\s", fld("author")) if a.strip()], "venue": fld("journal") or fld("booktitle"), "mine": False})
    return out


def read_pdfs(folder, email, key, mine_dir="mine"):
    import fitz  # pymupdf
    out = []
    for pdf in sorted(Path(folder).rglob("*.pdf")):
        try:
            doc = fitz.open(pdf)
            text = "\n".join(doc[i].get_text() for i in range(min(3, len(doc))))
            meta_title = (doc.metadata or {}).get("title") or ""
        except Exception:
            continue
        d = norm_doi(text)
        rec = {"doi": d, "mine": mine_dir in pdf.parts, "file": str(pdf)}
        if not d:
            t = meta_title.strip() or next((l.strip() for l in text.splitlines() if len(l.strip()) > 20), pdf.stem)
            found = search_title(t, email, key)
            if found:
                rec.update(found)
            else:
                rec.update({"title": t, "abstract": ""})
        out.append(rec)
    return out


def ingest(src, email="", key="", mine_dir="mine"):
    p = Path(src)
    if p.is_dir():
        recs = read_pdfs(p, email, key, mine_dir)
    else:
        ext = p.suffix.lower()
        recs = {".txt": read_txt, ".csv": read_csv, ".jsonl": read_jsonl, ".json": read_jsonl, ".bib": read_bib}[ext](p)
    recs = resolve(recs, email, key)
    seen, out = set(), []
    for r in recs:
        k = r.get("doi") or re.sub(r"\W+", " ", (r.get("title") or "").lower())[:80]
        if not k or k in seen or not r.get("title"):
            continue
        seen.add(k)
        out.append({"id": ("doi:" + r["doi"]) if r.get("doi") else "t:" + re.sub(r"\W+", "_", r["title"].lower())[:60], "title": r["title"], "year": r.get("year"), "doi": r.get("doi") or None,
                    "authors": r.get("authors") or [], "venue": r.get("venue") or "", "abstract": r.get("abstract") or "", "cites": r.get("cites") or 0, "url": r.get("url") or None, "mine": bool(r.get("mine"))})
    return out
