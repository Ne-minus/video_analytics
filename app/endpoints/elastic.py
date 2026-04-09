from fastapi import APIRouter, status, HTTPException
from app.services.es_client import es_client, create_index_if_not_exists, delete_index, index_exists
from functools import wraps

def handle_es_errors(func):
    """Декоратор для обработки ошибок Elasticsearch"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Elasticsearch error: {str(e)}")
    return wrapper

elastic_router = APIRouter()

@elastic_router.post("/init_index", status_code=201)
@handle_es_errors
async def init_index():
    """Создаёт индекс с маппингом и настройками, если он не существует"""
    await create_index_if_not_exists()
    return {"message": "Index ready"}

@elastic_router.get("/health")
@handle_es_errors
async def health():
    """Проверяет доступность Elasticsearch"""
    await es_client.info()
    return {"status": "ok"}

@elastic_router.delete("/delete_index", status_code=204)
@handle_es_errors
async def delete_index_endpoint():
    """Удаляет индекс"""
    await delete_index()

@elastic_router.get("/exists")
@handle_es_errors
async def index_exists_endpoint():
    """Проверяет существование индекса"""
    exists = await index_exists()
    return {"exists": bool(exists)}