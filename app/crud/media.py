from app.models.documents import MediaDocument
from app.es_client import es_client 
from app.core.es_config import INDEX_NAME
from elasticsearch import NotFoundError

async def create_document(doc: MediaDocument) -> str:
    """Индексирует документ, используя document_id как _id."""
    doc_dict = doc.model_dump(by_alias=True, exclude={"_id"})
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