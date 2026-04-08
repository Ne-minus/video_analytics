from typing import TypedDict


class VLMOutput(TypedDict):
    people_count: int
    people_present: bool
    people_summary: str
    scene_description: str
