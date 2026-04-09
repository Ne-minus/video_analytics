import io
import logging

from gigachat import GigaChat

from img2vlm.shared.config import settings
from img2vlm.shared.types import VLMOutput

logger = logging.getLogger(__name__)


class VLMClient:
    def __init__(self) -> None:
        self._giga = GigaChat(
            credentials=settings.gigachat_api_key,
            base_url=settings.gigachat_base_url,
            scope=settings.gigachat_scope,
            verify_ssl_certs=False,
        )

    async def close(self) -> None:
        await self._giga.aclose()

    async def _upload_image_to_gigachat(self, image_bytes: bytes, filename: str) -> str:
        if not settings.gigachat_api_key:
            raise RuntimeError("GIGACHAT_API_KEY is empty")

        file_obj = io.BytesIO(image_bytes)
        file_obj.name = filename

        try:
            uploaded_file = await self._giga.aupload_file(file_obj)
            return uploaded_file.id_
        except Exception as exc:
            logger.exception("Failed to upload image to GigaChat")
            raise RuntimeError(f"GigaChat upload failed: {exc}") from exc

    async def describe_image(self, image_bytes: bytes, filename: str, content_type: str | None) -> VLMOutput:
        file_id = await self._upload_image_to_gigachat(image_bytes, filename)

        try:
            scene_description = await self._request_scene_description(file_id)
            return {
                "scene_description": scene_description,
            }
        except (AttributeError, IndexError) as exc:
            logger.exception("Unexpected GigaChat response")
            raise RuntimeError("Unexpected GigaChat response format") from exc
        except Exception as exc:
            logger.exception("GigaChat request failed")
            raise RuntimeError(f"GigaChat request failed: {exc}") from exc

    async def _request_scene_description(self, file_id: str) -> str:
        # Use the same payload shape as the working notebook example:
        # client.chat({"messages":[{"role":"user","content":...,"attachments":[...]}], "temperature": ...})
        payload = {
            "model": settings.gigachat_model,
            "messages": [
                {
                    "role": "user",
                    "content": settings.gigachat_scene_prompt,
                    "attachments": [file_id],
                }
            ],
            "temperature": 0.2,
        }
        response = await self._giga.achat(payload)
        return response.choices[0].message.content.strip()
