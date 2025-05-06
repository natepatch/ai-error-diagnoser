import faiss
import pickle
import os
from sentence_transformers import SentenceTransformer

INDEX_PATH = "codebase.index"
METADATA_PATH = "codebase_metadata.pkl"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

def load_index_and_metadata():
    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        raise FileNotFoundError("❌ Index or metadata file not found. Run embed_codebase.py first.")

    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata

def search_similar_snippets(query: str, top_k: int = 5) -> list[str]:
    print("🔄 Loading model and index...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    index, metadata = load_index_and_metadata()

    print("🔍 Embedding query...")
    embedding = model.encode([query])
    print(f"🔎 Searching top {top_k} matches...")
    distances, indices = index.search(embedding, top_k)

    return [metadata[i] for i in indices[0] if i < len(metadata)]
