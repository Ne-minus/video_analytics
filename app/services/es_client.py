from elasticsearch import AsyncElasticsearch
from app.core.config import settings

es_client = AsyncElasticsearch(hosts=[settings.ES_HOST],
                                verify_certs=False,      # отключает проверку SSL-сертификата
                                ssl_show_warn=False)

async def create_index_if_not_exists():
    """Создаёт индекс с заданными настройками и маппингом, если его нет."""
    from app.core.es_config import INDEX_NAME, INDEX_SETTINGS, MAPPINGS
    if not await es_client.indices.exists(index=INDEX_NAME):
        await es_client.indices.create(
            index=INDEX_NAME,
            settings=INDEX_SETTINGS,
            mappings=MAPPINGS
        )

async def delete_index():
    """Удаляет индекс."""
    from app.core.es_config import INDEX_NAME
    await es_client.indices.delete(index=INDEX_NAME, ignore_unavailable=True)

async def index_exists() -> bool:
    """Проверяет существование индекса."""
    from app.core.es_config import INDEX_NAME
    return await es_client.indices.exists(index=INDEX_NAME)