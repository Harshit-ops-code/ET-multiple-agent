import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DB_PATH, EMBEDDING_MODEL
import os

os.makedirs(CHROMA_DB_PATH, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

def get_or_create_collection(name: str):
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

def upsert_documents(collection_name: str, documents: list[dict]):
    """
    documents = [{"id": str, "text": str, "metadata": dict}]
    """
    col = get_or_create_collection(collection_name)
    col.upsert(
        ids       = [d["id"]       for d in documents],
        documents = [d["text"]     for d in documents],
        metadatas = [d["metadata"] for d in documents],
    )
    return col

def query_collection(collection_name: str, query: str, n_results: int = 3):
    col = get_or_create_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    n = min(n_results, count)
    results = col.query(query_texts=[query], n_results=n)
    return [
        {
            "text":     results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]

def delete_collection(name: str):
    try:
        client.delete_collection(name)
    except Exception:
        pass