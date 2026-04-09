from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    messages: List[BaseMessage]

    # Parsed query for Elastic
    parsed: Dict[str, Any]  # {"text_query": str, "embedding_text": str, "top_k": int}
    embedding: List[float]

    user_query: str

    search_results: List[Dict[str, Any]]
    final_answer: str
    error: str
