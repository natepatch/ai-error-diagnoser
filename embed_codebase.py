import os
import re
from pathlib import Path
from dotenv import load_dotenv
import openai
from openai import OpenAI
import faiss
import json
import numpy as np

load_dotenv()
RAILS_ROOT = os.getenv("RAILS_REPO_PATH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not RAILS_ROOT:
    raise EnvironmentError("RAILS_REPO_PATH is not set")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY is not set")

INCLUDE_SUBDIRS = ["app", "lib", "graphql"]
EXCLUDE_DIRS = ["vendor", "node_modules", "tmp", "log"]
MAX_METHOD_LINES = 100
BATCH_SIZE = 100
MODEL_NAME = "text-embedding-3-large"
INDEX_FILE = "rails_methods.index"
METADATA_FILE = "rails_methods_meta.json"

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_methods(code: str):
    methods = []
    current = []
    inside = False
    depth = 0

    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("def "):
            inside = True
            depth = 1
            current = [line]
        elif inside:
            current.append(line)
            depth += line.count("do") + line.count("{") - line.count("end")
            if depth <= 0:
                method = "\n".join(current)
                if 1 < len(current) <= MAX_METHOD_LINES:
                    methods.append(method)
                inside = False
    return methods

def extract_class_or_module(code: str) -> str:
    match = re.search(r"^\s*(class|module)\s+([A-Za-z0-9_:]+)", code, re.MULTILINE)
    return match.group(2) if match else None

print("🔄 Loading and scanning Ruby files...")
all_paths = []
for subdir in INCLUDE_SUBDIRS:
    base = Path(RAILS_ROOT) / subdir
    if base.exists():
        all_paths += base.rglob("*.rb")

paths = [p for p in all_paths if not any(ex in str(p) for ex in EXCLUDE_DIRS)]
print(f"📁 Found {len(paths)} .rb files to scan")

texts = []
metadatas = []

for path in paths:
    try:
        content = path.read_text(encoding="utf-8")

        if "mailer" in str(path).lower():
            continue

        class_name = extract_class_or_module(content)
        methods = extract_methods(content)

        for method in methods:
            texts.append(method)
            metadatas.append({
                "path": str(path),
                "class_or_module": class_name,
                "snippet": method
            })

    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

print(f"🧠 Extracted {len(texts)} methods. Embedding with {MODEL_NAME} in batches of {BATCH_SIZE}...")

all_embeddings = []

for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i:i + BATCH_SIZE]
    try:
        response = client.embeddings.create(input=batch, model=MODEL_NAME)
        all_embeddings.extend([r.embedding for r in response.data])
    except Exception as e:
        print(f"❌ Error embedding batch {i}-{i+BATCH_SIZE}: {e}")

if not all_embeddings:
    raise RuntimeError("No embeddings generated")

embeddings = np.array(all_embeddings)
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print(f"💾 Saving index to {INDEX_FILE} and metadata to {METADATA_FILE}...")
faiss.write_index(index, INDEX_FILE)
with open(METADATA_FILE, "w") as f:
    json.dump(metadatas, f, indent=2)

print("✅ Embedding complete. Total methods embedded:", len(embeddings))
