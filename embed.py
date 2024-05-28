import datetime as dt
from diskcache import Cache
import srsly
import modal
from sentence_transformers import SentenceTransformer
from itertools import islice
from pathlib import Path

GPU_CONFIG = 'any'
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

app = modal.App("embed_stuff")
image = (modal.Image.debian_slim()
         .pip_install("sentence_transformers", "srsly", "diskcache")
         .run_commands(f"python -c 'from sentence_transformers import SentenceTransformer; tfm = SentenceTransformer(\"{EMBEDDING_MODEL}\")'"))


@app.function(image=image, gpu="any", enable_memory_snapshot=True)
def fetch_vectors(batch):
    tfm = SentenceTransformer(EMBEDDING_MODEL)
    return tfm.encode([t for t in batch])


def batched(iterable, n=10):
    """Batch data into lists of length n. The last batch may be shorter."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch

@app.local_entrypoint()
def main(jsonl_file, jsonl_col='text', cache_name=None):
	cache = Cache(Path(cache_name) / EMBEDDING_MODEL)
	texts = (d[jsonl_col] for d in srsly.read_jsonl(jsonl_file) if d[jsonl_col] not in cache)
	for batch in batched(texts):
		vectors = fetch_vectors.remote(batch)
		for t, v in zip(batch, vectors):
			cache[t] = v
		print(f'Just did another batch. {dt.datetime.now()}')
