from app.models.documents import MediaDocument
from app.services.es_client import es_client 
from app.services.embedding_service import embedding_service
from app.core.es_config import INDEX_NAME
from elasticsearch import NotFoundError
from typing import Any, Dict, List
from app.core.config import settings



async def create_document(doc_in: MediaDocument) -> str:
    embedding_list = await embedding_service.encode([doc_in.description])
    dense_vector = embedding_list[0]
    doc_dict = {
        "description": doc_in.description,
        "dense_vector": dense_vector,
        "created_at": doc_in.created_at,
        "updated_at": doc_in.updated_at,
    }
    response = await es_client.index(
        index=INDEX_NAME,
        id=doc_in.document_id,
        document=doc_dict,
        refresh=True
    )
    return response["_id"]

async def get_document(doc_id: str) -> MediaDocument | None:
    """Возвращает документ по ID или None."""
    try:
        response = await es_client.get(index=INDEX_NAME, id=doc_id)
        source = response["_source"]
        source["_id"] = response["_id"]
        return MediaDocument(**source)
    except NotFoundError:
        return None

async def delete_document(doc_id: str) -> bool:
    """Удаляет документ. Возвращает True, если документ существовал."""
    try:
        await es_client.delete(index=INDEX_NAME, id=doc_id, refresh=True)
        return True
    except NotFoundError:
        return False
    

async def search_documents(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    text_query = str(payload.get("text_query") or "").strip()
    embedding_list = await embedding_service.encode([text_query])
    embedding = embedding_list[0]

    try:
        top_k = int(payload.get("top_k") or 5)
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 50))

    # 1) Сначала semantic search по всем документам с dense_vector
    if isinstance(embedding, list) and len(embedding) > 0:
        base_semantic_query: Dict[str, Any] = {
            "bool": {
                "filter": [
                    {"exists": {"field": "dense_vector"}}
                ]
            }
        }

        # 2) Потом текст как дополнительный буст
        if text_query:
            base_semantic_query["bool"]["should"] = [
                {"match": {"description": {"query": text_query, "boost": 2.0}}}
            ]

        query: Dict[str, Any] = {
            "script_score": {
                "query": base_semantic_query,
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'dense_vector') + 1.0",
                    "params": {"query_vector": embedding},
                },
            }
        }

    else:
        # Если embedding нет, fallback на обычный текстовый поиск
        if text_query:
            query = {"match": {"description": {"query": text_query}}}
        else:
            query = {"match_all": {}}

    resp = await es_client.search(
        index=INDEX_NAME,
        query=query,
        size=top_k,
        _source_includes=["description"],
    )

    hits = (resp.get("hits") or {}).get("hits") or []
    results: List[Dict[str, Any]] = []
    for h in hits:
        src = h.get("_source") or {}
        results.append(
            {
                "document_id": h.get("_id") or src.get("document_id") or "",
                "scene_description": src.get("description") or "",
                "score": h.get("_score"),
            }
        )
    return results