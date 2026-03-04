import uuid
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from config import settings


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def ensure_collection(client: QdrantClient, vector_size: int = 1536):
    """Create collection if not exists."""
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )


def get_embedding(text: str, api_key: str = None) -> list[float]:
    """Get embedding vector for text."""
    provider = settings.EMBEDDING_PROVIDER
    model = settings.EMBEDDING_MODEL

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        response = client.embeddings.create(input=text, model=model)
        return response.data[0].embedding
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def embed_and_store(chunks: list[str], document_id: str, filename: str, api_key: str = None) -> int:
    """Embed chunks and store in Qdrant. Returns number of chunks stored."""
    client = get_qdrant_client()

    # Get vector size from first embedding
    if not chunks:
        return 0

    first_vec = get_embedding(chunks[0], api_key=api_key)
    ensure_collection(client, vector_size=len(first_vec))

    points = []
    for i, chunk in enumerate(chunks):
        vec = get_embedding(chunk, api_key=api_key) if i > 0 else first_vec
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunk,
            }
        ))

    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return len(points)


def delete_document_chunks(document_id: str):
    """Remove all chunks for a document from Qdrant."""
    client = get_qdrant_client()
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )
    )


def search_similar(query: str, top_k: int = 5, api_key: str = None) -> list[dict]:
    """Search for similar chunks."""
    client = get_qdrant_client()
    query_vec = get_embedding(query, api_key=api_key)
    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vec,
        limit=top_k,
        with_payload=True
    )
    return [{"text": r.payload.get("text", ""), "score": r.score, "filename": r.payload.get("filename", "")} for r in results]
