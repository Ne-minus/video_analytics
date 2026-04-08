import io
import json
import logging
from typing import Any

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from img2vlm.shared.config import settings
from img2vlm.shared.types import VLMOutput

logger = logging.getLogger(__name__)


class VLMClient:
    def __init__(self) -> None:
        self._giga = GigaChat(
            credentials=settings.gigachat_api_key,
            base_url=settings.gigachat_base_url,
            scope="GIGACHAT_API_CORP",
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
            people_analysis = await self._request_people_analysis(file_id)
            scene_description = await self._request_scene_description(file_id)
            return {
                "people_count": people_analysis["people_count"],
                "people_present": people_analysis["people_present"],
                "people_summary": people_analysis["people_summary"],
                "scene_description": scene_description,
            }
        except (AttributeError, IndexError) as exc:
            logger.exception("Unexpected GigaChat response")
            raise RuntimeError("Unexpected GigaChat response format") from exc
        except Exception as exc:
            logger.exception("GigaChat request failed")
            raise RuntimeError(f"GigaChat request failed: {exc}") from exc

    async def _request_people_analysis(self, file_id: str) -> dict[str, Any]:
        payload = Chat(
            model=settings.gigachat_model,
            messages=[
                Messages(
                    role=MessagesRole.USER,
                    content=settings.gigachat_people_prompt,
                    attachments=[file_id],
                )
            ],
            temperature=0.1,
        )
        response = await self._giga.achat(payload)
        raw_content = response.choices[0].message.content.strip()
        return self._parse_people_json(raw_content)

    async def _request_scene_description(self, file_id: str) -> str:
        payload = Chat(
            model=settings.gigachat_model,
            messages=[
                Messages(
                    role=MessagesRole.USER,
                    content=settings.gigachat_scene_prompt,
                    attachments=[file_id],
                )
            ],
            temperature=0.2,
        )
        response = await self._giga.achat(payload)
        return response.choices[0].message.content.strip()

    def _parse_people_json(self, raw_content: str) -> dict[str, Any]:
        normalized = raw_content.strip()
        if normalized.startswith("```"):
            normalized = normalized.strip("`")
            if normalized.startswith("json"):
                normalized = normalized[4:].strip()

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            logger.exception("Failed to parse GigaChat JSON output: %s", raw_content)
            raise RuntimeError("GigaChat returned invalid JSON")

        try:
            people_count = int(parsed["people_count"])
            people_present = bool(parsed["people_present"])
            people_summary = str(parsed["people_summary"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            logger.exception("GigaChat JSON missing required fields: %s", parsed)
            raise RuntimeError("GigaChat JSON response is missing required fields") from exc

        return {
            "people_count": max(0, people_count),
            "people_present": people_present if people_count > 0 else False,
            "people_summary": people_summary,
        }
