
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import pickle

# Config
CODE_DIR = "app"  # path to root code folder
MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_FILE = "codebase.index"
METADATA_FILE = "codebase_metadata.pkl"

# Load model
print("🔄 Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

# Gather Ruby files
print(f"🔍 Indexing Ruby files in {CODE_DIR}/...")
paths = list(Path(CODE_DIR).rglob("*.rb"))

texts = []
metadatas = []

for path in paths:
    try:
        with open(path, "r") as f:
            content = f.read()
        if len(content.strip()) == 0:
            continue
        texts.append(content)
        metadatas.append({"path": str(path)})
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

# Embed
print(f"🧠 Generating {len(texts)} embeddings...")
embeddings = model.encode(texts, convert_to_tensor=False)

# Save FAISS index
d = embeddings[0].shape[0]
index = faiss.IndexFlatL2(d)
index.add(embeddings)

print(f"💾 Saving index to {INDEX_FILE} and metadata to {METADATA_FILE}...")
faiss.write_index(index, INDEX_FILE)

with open(METADATA_FILE, "wb") as f:
    pickle.dump(metadatas, f)

print("✅ Done.")
