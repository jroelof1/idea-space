# Instructions for an AI assistant setting up Idea Space

You are reading this because a person gave you this repository and asked you to build their own Idea Space, a 3D browser map of the ideas in a collection of text they care about (papers, notes, essays, legal opinions, transcripts, archives, or anything with a title and a few sentences of description). Read this file and `README.md`, then follow the steps below. Do the work yourself where you can, and ask the person only for the things listed under "What you need from the person".

## What this tool does

It reads a list of items (DOIs, a CSV, BibTeX, or a folder of PDFs), fills in titles and abstracts from OpenAlex for scholarly works, embeds them, lays them out in 3D, and writes one self-contained file, `workspace/idea_space.html`, that the person opens in a browser. An optional step uses Claude to tag what each paper does in field-neutral words. Nothing from this repository is specific to any one research field.

## What you need from the person

Ask for these in one message, and do not start the build until you have the first three.

1. **Their items.** An item is a paper, note, passage, opinion, transcript segment or anything else with a title and a few sentences of description. Any of these works: a list of DOIs or arXiv ids, a CSV or BibTeX export from a reference manager (Zotero, Mendeley, EndNote), JSONL, or a folder of PDFs. If their items are scholarly, they can give DOIs or a reference-manager export. If they only describe a topic, offer to find candidate papers with OpenAlex or a literature search and show them the list to approve before you use it. If their items are not scholarly (notes, essays, opinions, transcripts), build a CSV with `title` and `abstract` columns (the description) and a `year` column for the date, and no OpenAlex lookup is needed for those. Cut long texts into passages first, one row per passage with a short title. They can mark their own papers (end a DOI line with `*`, put `mine` in the CSV column, or put PDFs in a subfolder named `mine`).
2. **An email address.** It is sent to OpenAlex as the contact for polite use.
3. **A free OpenAlex API key** (only needed when they supply DOIs, arXiv ids, BibTeX or PDFs; skip it for a CSV that already has descriptions) from https://openalex.org/settings/api. OpenAlex refuses requests without one, so the tool stops with an error message if it is missing.
4. **Optional, an Anthropic API key** (environment variable `ANTHROPIC_API_KEY`) for the tagging step. Without it, everything still works and the map is built from the text embeddings alone. Tell the person that tagging sends their paper titles and abstracts to Anthropic and costs a small amount per paper, and let them choose.

## Setup steps

Work in the repository folder.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit `config.yaml` to add `email` and `openalex_key`. You can set the variables `IDEASPACE_EMAIL` and `OPENALEX_API_KEY` in the environment instead. `config.yaml` is git-ignored, and you must never print, log, commit or paste the keys anywhere.

Then run the pipeline with the person's papers:

```bash
python3 -m ideaspace ingest PATH_TO_PAPERS      # writes workspace/papers.jsonl and reports how many have abstracts
python3 -m ideaspace tag                        # optional, only with ANTHROPIC_API_KEY set
python3 -m ideaspace build                      # writes workspace/idea_space.html
```

`python3 -m ideaspace all PATH_TO_PAPERS` does the three steps in one go and skips tagging when no Anthropic key is set. Use `-w FOLDER` before the command to keep several libraries apart. The first run downloads an embedding model of about 400 MB, so allow a few minutes. A few hundred papers build in about two minutes and a few thousand in about ten.

## Check your work before you tell the person it is done

1. `python3 -m pytest -q tests` should pass.
2. Read the ingest report. If many papers have no abstract, tell the person, because those papers sit on the map by title alone and are placed less well. A CSV with an `abstract` column fixes this.
3. The build needs at least 12 papers and says so if there are fewer. A map is most useful with 50 or more.
4. Open `workspace/idea_space.html` (or give the person its path) and say what to try first: click a paper, press **Cross-field links** in its card, open **Principles**, and paste a sentence of their own thinking into **Paste an idea**.

## Adding papers later

Run `python3 -m ideaspace ingest NEW_FILE --add`, then `python3 -m ideaspace tag` if they use tags, then `python3 -m ideaspace build`. Embeddings and tags are cached, so only the new papers cost time.

## Changing what the tags mean

`vocab.yaml` defines the operations and evidence kinds used by the tagger. They are written for science, so for other material (law, history, writing, organisations) rewrite them in the person's own terms before tagging. If the person's field needs different words, edit the descriptions there (keep the names short and in snake_case) and rerun `tag` on a fresh `workspace/facets.jsonl`. The tagger only accepts names that appear in this file.

## Problems you may meet

| Symptom | Cause and fix |
|---|---|
| "OpenAlex refused the request because no API key was given" | The key is missing. Set `openalex_key` in `config.yaml` or `OPENALEX_API_KEY`. |
| Fewer papers than expected after ingest | A DOI was not found in OpenAlex, or a duplicate was removed. Papers without a title are dropped. |
| `0 papers` from a PDF folder | The PDFs have no DOI on the first pages. The tool then searches by title, and scanned PDFs with no text layer cannot be read. A DOI or CSV list is more reliable. |
| "Only N papers. Add at least 12" | The map needs more papers to lay out. |
| Tagging stops or returns fewer records | Rerun `tag`. It resumes and only tags papers that are missing. |
| Slow first build | The embedding model is downloading. It is cached afterwards. |

## Rules to follow

- Do not invent items, DOIs or descriptions. If a record cannot be resolved, say so.
- Do not send the person's data anywhere except OpenAlex (DOI lookups only) and Anthropic (tagging, only if they agreed).
- Treat the clusters and links as suggestions from text similarity. When you describe a connection to the person, say that it is a prompt to read both items and that it does not show a real relationship.
- Keep the person's papers and keys out of version control. `workspace/` and `config.yaml` are already git-ignored.
