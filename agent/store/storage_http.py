import os
from typing import Any, Dict, List, Optional

import httpx


class StorageHttpStore:
    """
    Реализация Store, которая обращается к сервису storage по HTTP.

    Ожидает у storage эндпоинт:
      POST /media/search  { text_query, embedding, top_k } -> list[...]
    """

    def __init__(self, base_url: Optional[str] = None, timeout_s: float = 20.0) -> None:
        self.base_url = (base_url or os.getenv("STORAGE_URL") or "http://localhost:8000").rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout_s)

    async def asearch(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        r = await self._client.post("/media/search", json=payload)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return []

    def search(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        # sync fallback: запускаем отдельный клиент без event loop
        with httpx.Client(base_url=self.base_url, timeout=self._client.timeout) as c:
            r = c.post("/media/search", json=payload)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            return []

    async def aclose(self) -> None:
        await self._client.aclose()

