import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import numpy as np

# Config
CODE_DIR = "app"  # Path to root of your codebase
MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_FILE = "codebase.index"
METADATA_FILE = "codebase_metadata.pkl"

# Load embedding model
print("🔄 Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

# Gather Ruby files
print(f"🔍 Indexing Ruby files in {CODE_DIR}/...")
paths = list(Path(CODE_DIR).rglob("*.rb"))

texts = []
metadatas = []

for path in paths:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            continue
        texts.append(content)
        metadatas.append({
            "path": str(path),
            "code": content.strip()
        })
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

# Generate embeddings
print(f"🧠 Generating {len(texts)} embeddings...")
embeddings = model.encode(texts, convert_to_tensor=False)
embeddings = np.array(embeddings)

# Save FAISS index
dimension = embeddings[0].shape[0]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print(f"💾 Saving index to {INDEX_FILE} and metadata to {METADATA_FILE}...")
faiss.write_index(index, INDEX_FILE)

with open(METADATA_FILE, "wb") as f:
    pickle.dump(metadatas, f)

print("✅ Codebase embedding complete.")
