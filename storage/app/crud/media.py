from storage.app.models.documents import MediaDocument
from storage.app.es_client import es_client 
from storage.app.core.es_config import INDEX_NAME
from elasticsearch import NotFoundError
from typing import Any, Dict, List
from storage.app.core.config import settings

async def create_document(doc: MediaDocument) -> str:
    """Индексирует документ, используя document_id как _id."""
    # В модели `document_id` имеет alias `_id`, а Elasticsearch запрещает `_id` внутри тела документа.
    # Поэтому сериализуем без alias'ов и исключаем `document_id`, передавая id отдельно.
    doc_dict = doc.model_dump(by_alias=False, exclude={"document_id"})
    vec = doc_dict.get("dense_vector")
    if isinstance(vec, list):
        dims = int(settings.ES_VECTOR_DIMS)
        if dims > 0:
            if len(vec) > dims:
                doc_dict["dense_vector"] = vec[:dims]
            elif len(vec) < dims:
                doc_dict["dense_vector"] = vec + ([0.0] * (dims - len(vec)))
        # Elasticsearch cosine similarity не принимает нулевой вектор (||v|| = 0).
        vec2 = doc_dict.get("dense_vector")
        if isinstance(vec2, list) and len(vec2) > 0:
            if all((float(x) == 0.0) for x in vec2):
                vec2[0] = 1e-6
                doc_dict["dense_vector"] = vec2
    response = await es_client.index(
        index=INDEX_NAME,
        id=doc.document_id,
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
    embedding = payload.get("embedding") or []

    try:
        top_k = int(payload.get("top_k") or 5)
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 50))

    # Нормализуем query embedding под размерность индекса
    if isinstance(embedding, list):
        dims = int(settings.ES_VECTOR_DIMS)
        if dims > 0:
            if len(embedding) > dims:
                embedding = embedding[:dims]
            elif len(embedding) < dims:
                embedding = embedding + ([0.0] * (dims - len(embedding)))

        if len(embedding) > 0 and all(float(x) == 0.0 for x in embedding):
            embedding[0] = 1e-6

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
