# Idea Space

> **Using an AI assistant?** Give it this repository and tell it to read `AGENTS.md`. That file lists what it needs from you and the exact steps to build your map.

Idea Space turns any collection of text into a 3D map of ideas you can explore in a browser. Each item sits where its meaning puts it, so items that say similar things are close together, and the tool helps you find connections between areas that normally never meet. You supply the items and it builds a single HTML file that works offline, with the 3D library included.

An item can be anything that has a title and a few sentences of description.

- **Research and scholarship:** papers, book chapters, theses, grant proposals, conference abstracts, the reading list of a whole field.
- **Law and policy:** court opinions, statutes, regulations, policy memos, patents.
- **History and the humanities:** letters, diaries, speeches, sermons, philosophical or religious texts cut into passages, archives of primary sources.
- **Writing and media:** essays, newsletters, a blog's back catalogue, podcast or lecture transcripts cut into segments, a novel's chapters.
- **Organisations:** meeting notes, product requirements, support tickets, customer feedback, interview transcripts, internal wikis.
- **Personal:** journals, saved articles, bookmarks, years of notes.

## What you get

- A 3D map of your items, laid out by the meaning of their titles and descriptions. Collections of thousands of items stay readable.
- **Cross-field links.** Select an item and link it to 1 to 10 items in other clusters that connect to it in unexpected ways, either close in meaning or sharing structure.
- **Principles.** Browse the operations, quantity dimensions, named laws and kinds of evidence that recur across clusters, and see which clusters share one.
- **Paste an idea.** Paste a phrase or paragraph and see where it resonates on the map. If Claude is available in your viewer, the idea is also restated in the vocabularies of other fields to bring out hidden connections.
- Tools to select and connect items, pull one and see what follows, place a sphere, find thin spots where the collection has little, re-weight the map around an idea (Lens), keep bookmarks and stars, save views, and filter by year and kind of evidence.

The structure tags (what each item does, in field-neutral words) are optional and come from Claude. Without them the map, search, clusters, cross-field links by meaning and Paste an idea all work from the text alone.

## Quick start

```bash
git clone <this repository>
cd idea-space
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml        # add your email and a free OpenAlex key
python3 -m ideaspace all example/dois.txt # ingest, tag (if ANTHROPIC_API_KEY is set) and build
open workspace/idea_space.html            # or double-click it
```

A free OpenAlex key (https://openalex.org/settings/api) is needed because OpenAlex no longer serves requests without one, and it is used to look up scholarly works. If your items are not scholarly works, you can supply the text yourself in a CSV and the key is not used. The first run downloads the embedding model (about 400 MB). A few hundred items build in a couple of minutes, and a few thousand in about ten.

## Bring your own items

`ideaspace ingest SOURCE` accepts any of these.

| Source | What to provide |
|---|---|
| a text file of DOIs | one DOI, DOI link or arXiv id per line. End a line with `*` to mark it as one of your own |
| a CSV | columns `title, abstract, year, doi, authors, venue, url, mine`. Only `title` is required. For items that are not papers, put the description in `abstract` and the date in `year` |
| JSONL or JSON | the same fields as the CSV |
| a BibTeX file | titles, abstracts and DOIs are read from the entries |
| a folder of PDFs | the DOI is found on the first pages, or the title is searched. Put your own in a subfolder named `mine` |

Missing abstracts for scholarly works are filled in from OpenAlex. Items marked as yours show in a different colour and are left out of the "like this" lists, so you can see where your own work sits among everything else. Add more later with `ideaspace ingest more.txt --add`, then run `ideaspace build` again. Embeddings are cached, so only new items cost time.

Text longer than a few paragraphs works best cut into passages, one item per passage, each with a short title. Very short items such as single words or posts of a line or two give a noisy map.

## The steps

```bash
python3 -m ideaspace ingest my_items.txt       # writes workspace/papers.jsonl
python3 -m ideaspace tag                       # optional, needs ANTHROPIC_API_KEY
python3 -m ideaspace build                     # writes workspace/idea_space.html
```

Use `-w FOLDER` before the command to keep several maps side by side.

### Tagging

`tag` sends titles and descriptions to Claude in small batches and stores the answers in `workspace/facets.jsonl`, so reruns only tag new items. Each item gets a one-sentence statement of its core structure, one to three operations, a kind of evidence, quantity dimensions, scales, named laws and a discipline label. The operation and evidence vocabularies live in `vocab.yaml`. They are written for science, so edit them to describe what happens in your own area. A legal map could use operations such as "grants a right" and "limits a power". The aim of the operations is to describe what an item does in words that do not belong to any one field, so that items from different areas that do similar things can be found next to each other.

Tagging costs a small amount per item on the Anthropic API (the default model is a small, fast one). Your titles and descriptions leave your machine for this step, and for the OpenAlex lookup when you use DOIs, and for nothing else.

## What this tool does not do

It does not check whether anything is true. It reads titles and descriptions and not full texts. It works best on English. The clusters and links are suggestions from similarity of wording and meaning, and the page labels them that way. A connection is a prompt to read both items, and the result does not show that they are related.

## Sharing a map

`workspace/idea_space.html` is one self-contained file. Sending it shares the titles and descriptions of everything in it, so check the licences and privacy of your material before you publish a map.

## Layout

```
ideaspace/ingest.py   read sources, fill metadata from OpenAlex
ideaspace/embed.py    embeddings with a cache
ideaspace/layout.py   hub-corrected distances, 3D layout, cluster names
ideaspace/tag.py      optional structure tags with Claude
ideaspace/build.py    assemble the page data and write the HTML
ideaspace/page/       the explorer page template
vocab.yaml            operations and evidence kinds used by the tagger
example/dois.txt      a small starter list from different fields
tests/                unit tests (python3 -m pytest)
```

## How the map is made

Titles and descriptions are embedded with BAAI/bge-base-en-v1.5. Distances are corrected for hubness, which stops generic items from looking close to everything (each distance is `2d - r_a - r_b`, where `r` is an item's mean distance to its ten nearest neighbours). A UMAP embedding of the corrected distances gives the 3D layout, and a short relaxation step spreads the points so that none sit on top of each other. Clusters come from Ward clustering of the embeddings and are named by the words that are most distinctive for each one.

## Licence

MIT, see LICENSE (copyright Josh Roeloffs). The page bundles three.js (MIT, see THIRD_PARTY.md). The starter list in `example/` is only a list of DOIs. Titles and abstracts are fetched from OpenAlex when you run it and are not stored in this repository.
