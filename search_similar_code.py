import logging
import faiss
import json
import openai
from pathlib import Path

logger = logging.getLogger(__name__)

INDEX_PATH = Path("rails_methods.index")
META_PATH = Path("rails_methods_meta.json")

if INDEX_PATH.exists() and META_PATH.exists():
    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH) as f:
        METADATA = json.load(f)
    INDEXED_CODE_SNIPPETS = [item["snippet"] for item in METADATA]
else:
    logger.warning("Index or metadata missing. Fallback search only.")
    index = None
    METADATA = []
    INDEXED_CODE_SNIPPETS = []

GRAPHQL_HINT_KEYWORDS = [
    "context[:current_user]", "ExecutionError", "resolve(", "find_by(", ".becomes(", "GraphQL::ExecutionError"
]

def snippet_keyword_score(snippet: str) -> int:
    return sum(1 for kw in GRAPHQL_HINT_KEYWORDS if kw in snippet)

def get_embedding(text: str) -> list:
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-3-large"
    )
    return response["data"][0]["embedding"]

def vector_search(query: str, top_k: int = 5, class_hint: str = None) -> list:
    if index is None:
        return []

    query_vec = get_embedding(query)
    D, I = index.search([query_vec], top_k * 3)  # over-fetch
    results = []

    for j, i in enumerate(I[0]):
        if i >= len(METADATA):
            continue
        score = 1.0 / (1.0 + D[0][j])  # invert distance
        snippet_meta = METADATA[i]
        snippet_meta["score"] = score
        snippet_meta["keyword_score"] = snippet_keyword_score(snippet_meta["snippet"])

        # Optional class/module context boosting
        if class_hint and snippet_meta.get("class_or_module") and class_hint in snippet_meta["class_or_module"]:
            snippet_meta["class_boost"] = 1
        else:
            snippet_meta["class_boost"] = 0

        results.append(snippet_meta)

    return results

def keyword_fallback_search(query: str, top_k: int) -> list:
    keywords = set(query.lower().split())
    matches = []

    for snippet in INDEXED_CODE_SNIPPETS:
        if any(keyword in snippet.lower() for keyword in keywords):
            matches.append(snippet)
        if len(matches) >= top_k:
            break

    return matches

def search_similar_snippets(query: str, top_k: int = 5, min_score: float = 0.5, class_hint: str = None) -> list:
    logger.debug("Searching for similar code snippets...")
    logger.debug(f"Query:\n{query}")

    try:
        results = vector_search(query, top_k=top_k, class_hint=class_hint)

        results.sort(
            key=lambda r: (
                r.get("class_boost", 0),
                r.get("keyword_score", 0),
                r.get("score", 0)
            ),
            reverse=True
        )

        strong_results = [r["snippet"] for r in results if r.get("score", 1.0) >= min_score][:top_k]

        if strong_results:
            logger.debug(f"✅ Returning {len(strong_results)} class-aware matches.")
            return strong_results
        else:
            logger.warning("⚠️ No strong vector matches found. Falling back to keyword search.")
    except Exception as e:
        logger.exception("Vector search failed. Falling back to keyword match.")

    return keyword_fallback_search(query, top_k=top_k)
