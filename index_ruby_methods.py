import os
import re
import faiss
import openai
import tiktoken
from pathlib import Path
from typing import List, Tuple

openai.api_key = os.getenv("OPENAI_API_KEY")

ENCODING = tiktoken.encoding_for_model("text-embedding-3-small")
MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

def get_ruby_files(root_dir: str) -> List[Path]:
    return list(Path(root_dir).rglob("*.rb"))

def extract_methods_from_file(file_path: Path) -> List[Tuple[str, str]]:
    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    methods = []
    class_context = None

    lines = code.splitlines()
    block = []
    inside_method = False
    depth = 0

    for line in lines:
        stripped = line.strip()
        if re.match(r'^(class|module)\s+\w+', stripped):
            class_context = stripped
        if stripped.startswith("def "):
            inside_method = True
            depth = 1
            block = [line]
        elif inside_method:
            block.append(line)
            depth += line.count("do") + line.count("{") - line.count("end")
            if depth <= 0:
                methods.append(("\n".join(block), str(file_path)))
                inside_method = False
    return methods

def get_embedding(text: str) -> List[float]:
    response = openai.Embedding.create(
        input=[text],
        model=MODEL
    )
    return response["data"][0]["embedding"]

def index_methods(methods: List[Tuple[str, str]]):
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    metadata = []

    for method, path in methods:
        try:
            if len(ENCODING.encode(method)) > 8191:
                continue  # skip too-long inputs
            vec = get_embedding(method)
            index.add([vec])
            metadata.append({"snippet": method, "path": path})
        except Exception as e:
            print(f"Embedding failed for method in {path}: {e}")

    return index, metadata

def main():
    root = os.getenv("RAILS_PROJECT_PATH", ".")
    ruby_files = get_ruby_files(root)
    all_methods = []

    for file_path in ruby_files:
        all_methods.extend(extract_methods_from_file(file_path))

    print(f"✅ Extracted {len(all_methods)} methods from {len(ruby_files)} files")

    index, metadata = index_methods(all_methods)

    # Save to disk or return
    faiss.write_index(index, "rails_methods.index")
    with open("rails_methods_meta.json", "w") as f:
        import json
        json.dump(metadata, f, indent=2)

    print("✅ Indexing complete. Stored in 'rails_methods.index' and metadata JSON.")

if __name__ == "__main__":
    main()
