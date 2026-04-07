from fastapi import APIRouter, HTTPException, status
from app.models.documents import MediaDocument
from app.crud.media import create_document, get_document, delete_document

media_router = APIRouter()

@media_router.post("/", response_model=MediaDocument, status_code=status.HTTP_201_CREATED)
async def create_doc(doc: MediaDocument):
    """Создать документ в Elasticsearch"""
    doc_id = await create_document(doc)
    # Возвращаем созданный документ с заполненным _id
    created_doc = await get_document(doc_id)
    return created_doc

@media_router.get("/{doc_id}", response_model=MediaDocument, status_code=status.HTTP_200_OK)
async def get_doc(doc_id: str):
    """Получить документ по ID"""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )
    return doc

@media_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(doc_id: str):
    """Удалить документ по ID"""
    deleted = await delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )
    return None