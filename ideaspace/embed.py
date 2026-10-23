"""Text embeddings with a small on-disk cache, so rebuilding after adding papers only embeds the new ones."""
import hashlib
from pathlib import Path
import numpy as np

MODEL = "BAAI/bge-base-en-v1.5"
_m = {}


def _model(name):
    if name not in _m:
        from sentence_transformers import SentenceTransformer
        _m[name] = SentenceTransformer(name, device="cpu")
    return _m[name]


def embed(texts, cache_dir, name=MODEL):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / "vectors.npz"
    cache = dict(np.load(f)) if f.exists() else {}
    keys = [hashlib.sha1((name + "|" + t).encode()).hexdigest() for t in texts]
    need = [i for i, k in enumerate(keys) if k not in cache]
    if need:
        v = _model(name).encode([texts[i] for i in need], batch_size=32, normalize_embeddings=True, show_progress_bar=len(need) > 50)
        for i, row in zip(need, v):
            cache[keys[i]] = np.asarray(row, dtype="float32")
        np.savez(f, **cache)
    return np.vstack([cache[k] for k in keys]).astype("float32")
