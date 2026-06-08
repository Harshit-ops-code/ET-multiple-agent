import math
import os
import re
from collections import Counter

from config import CHROMA_DB_PATH, EMBEDDING_MODEL

os.makedirs(CHROMA_DB_PATH, exist_ok=True)

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None


_fallback_collections: dict[str, list[dict]] = {}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine_distance(left: str, right: str) -> float:
    left_counts = Counter(_tokenize(left))
    right_counts = Counter(_tokenize(right))
    if not left_counts or not right_counts:
        return 1.0

    terms = set(left_counts) | set(right_counts)
    dot = sum(left_counts[t] * right_counts[t] for t in terms)
    left_norm = math.sqrt(sum(v * v for v in left_counts.values()))
    right_norm = math.sqrt(sum(v * v for v in right_counts.values()))
    if not left_norm or not right_norm:
        return 1.0

    similarity = dot / (left_norm * right_norm)
    return max(0.0, min(1.0, 1.0 - similarity))


if chromadb is not None:
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    except Exception as e:
        print(f"[RAG] Failed to initialize ChromaDB or SentenceTransformer (falling back to lexical): {e}")
        chromadb = None
        client = None
        embedding_fn = None
else:
    client = None
    embedding_fn = None
    print("[RAG] chromadb is not installed - using lexical local retrieval")


def get_or_create_collection(name: str):
    if client is None:
        _fallback_collections.setdefault(name, [])
        return name

    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_documents(collection_name: str, documents: list[dict]):
    if client is None:
        collection = _fallback_collections.setdefault(collection_name, [])
        by_id = {doc["id"]: doc for doc in collection}
        for doc in documents:
            by_id[doc["id"]] = doc
        _fallback_collections[collection_name] = list(by_id.values())
        return collection_name

    col = get_or_create_collection(collection_name)
    col.upsert(
        ids=[d["id"] for d in documents],
        documents=[d["text"] for d in documents],
        metadatas=[d["metadata"] for d in documents],
    )
    return col


def query_collection(collection_name: str, query: str, n_results: int = 3):
    if client is None:
        collection = _fallback_collections.get(collection_name, [])
        ranked = sorted(
            collection,
            key=lambda doc: _cosine_distance(query, doc.get("text", "")),
        )
        return [
            {
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "distance": _cosine_distance(query, doc.get("text", "")),
            }
            for doc in ranked[:n_results]
        ]

    col = get_or_create_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    n = min(n_results, count)
    results = col.query(query_texts=[query], n_results=n)
    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]


def delete_collection(name: str):
    if client is None:
        _fallback_collections.pop(name, None)
        return

    try:
        client.delete_collection(name)
    except Exception:
        pass
