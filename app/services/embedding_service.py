from app.core.config import settings
from typing import List
from gigachat import GigaChat

class Embedder:
    def __init__(self):
        self._giga: GigaChat | None = None

    def _get_client(self) -> GigaChat:
        """Ленивая инициализация"""
        if self._giga is None:
            self._giga = GigaChat(
                credentials=settings.GIGACHAT_API_KEY,
                base_url=settings.GIGACHAT_BASE_URL,
                scope="GIGACHAT_API_CORP",
                verify_ssl_certs=False,
            )
        return self._giga

    
    async def encode(self, texts: List[str]) -> List[List[float]]:
        """Преобразуем текст в эмбеддинги"""
        client = self._get_client()
        result = await client.aembeddings(texts)
        return [item.embedding for item in result.data]
    
embedding_service = Embedder()