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


DATABASE_URL = os.getenv("DATABASE_URL")
_use_postgres = bool(DATABASE_URL)


def _connect_postgres():
    import pg8000
    import urllib.parse
    import ssl

    url = urllib.parse.urlparse(DATABASE_URL)
    database = url.path[1:]
    port = url.port or 5432

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = pg8000.connect(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=port,
        database=database,
        ssl_context=ssl_context
    )
    return conn


def _init_postgres_collections():
    if not _use_postgres:
        return
    conn = _connect_postgres()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                collection_name VARCHAR(255) NOT NULL,
                doc_id          VARCHAR(255) NOT NULL,
                document        TEXT NOT NULL,
                metadata        TEXT,
                PRIMARY KEY (collection_name, doc_id)
            )
        """)
        conn.commit()
        cursor.close()
    finally:
        conn.close()


if _use_postgres:
    try:
        _init_postgres_collections()
    except Exception as e:
        print(f"[RAG] Failed to initialize Postgres collections: {e}")


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


def _get_gemini_embedding(text: str) -> list[float] | None:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or "mock" in gemini_key.lower():
        return None

    # Try gemini-embedding-2 first, fallback to text-embedding-004
    for model_name in ("gemini-embedding-2", "text-embedding-004"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        body = {
            "model": f"models/{model_name}",
            "content": {
                "parts": [{"text": text}]
            }
        }
        try:
            import requests
            resp = requests.post(url, headers=headers, json=body, timeout=15)
            if resp.status_code == 200:
                return resp.json()["embedding"]["values"]
        except Exception:
            pass
    return None


def _vector_cosine_distance(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    norm_u = math.sqrt(sum(a * a for a in u))
    norm_v = math.sqrt(sum(a * a for a in v))
    if not norm_u or not norm_v:
        return 1.0
    similarity = dot / (norm_u * norm_v)
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
        if _use_postgres:
            return name
        _fallback_collections.setdefault(name, [])
        return name

    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_documents(collection_name: str, documents: list[dict]):
    if client is None:
        if _use_postgres:
            import json
            conn = _connect_postgres()
            try:
                cursor = conn.cursor()
                for doc in documents:
                    sql = """
                        INSERT INTO collections (collection_name, doc_id, document, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (collection_name, doc_id)
                        DO UPDATE SET document = EXCLUDED.document, metadata = EXCLUDED.metadata
                    """
                    cursor.execute(sql, (collection_name, doc["id"], doc["text"], json.dumps(doc["metadata"])))
                conn.commit()
                cursor.close()
            finally:
                conn.close()
            return collection_name

        collection = _fallback_collections.setdefault(collection_name, [])
        
        # Parallel embedding retrieval to minimize API latency
        from concurrent.futures import ThreadPoolExecutor
        
        def embed_doc(doc):
            emb = _get_gemini_embedding(doc["text"])
            return doc["id"], emb
            
        embeddings_map = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(embed_doc, d) for d in documents]
            for fut in futures:
                try:
                    doc_id, emb = fut.result()
                    if emb:
                        embeddings_map[doc_id] = emb
                except Exception:
                    pass
                    
        by_id = {doc["id"]: doc for doc in collection}
        for doc in documents:
            doc_copy = dict(doc)
            doc_copy["embedding"] = embeddings_map.get(doc["id"])
            by_id[doc["id"]] = doc_copy
            
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
        if _use_postgres:
            import json
            conn = _connect_postgres()
            collection = []
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT doc_id, document, metadata FROM collections WHERE collection_name = %s",
                    (collection_name,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    meta = json.loads(r[2]) if r[2] else {}
                    collection.append({
                        "id": r[0],
                        "text": r[1],
                        "metadata": meta
                    })
                cursor.close()
            finally:
                conn.close()
        else:
            collection = _fallback_collections.get(collection_name, [])

        query_emb = _get_gemini_embedding(query)

        def get_distance(doc):
            if query_emb and doc.get("embedding"):
                return _vector_cosine_distance(query_emb, doc["embedding"])
            return _cosine_distance(query, doc.get("text", ""))

        ranked = sorted(
            collection,
            key=get_distance,
        )
        return [
            {
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "distance": get_distance(doc),
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
        if _use_postgres:
            conn = _connect_postgres()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collections WHERE collection_name = %s", (name,))
                conn.commit()
                cursor.close()
            finally:
                conn.close()
            return

        _fallback_collections.pop(name, None)
        return

    try:
        client.delete_collection(name)
    except Exception:
        pass
