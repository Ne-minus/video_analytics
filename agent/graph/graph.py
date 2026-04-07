import json
import uuid
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import ValidationError

from agent.llm.giga_init import get_llm
from agent.prompts import PARSER_PROMPT
from agent.graph.state import AgentState
from agent.llm.embeddings import get_embeddings


llm = get_llm()
emb = get_embeddings()

def get_last_user_text(messages: List[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    raise ValueError("Не найдено сообщение пользователя")


def sanitize_parsed(parsed: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    text_query = str(parsed.get("text_query") or user_query).strip()
    embedding_text = str(parsed.get("embedding_text") or text_query).strip()
    try:
        top_k = int(parsed.get("top_k") or 5)
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 20))
    return {"text_query": text_query, "embedding_text": embedding_text, "top_k": top_k}

def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("JSON object not found", text, 0)
    return json.loads(text[start:end + 1])


def parse_query_node(state: AgentState) -> AgentState:
    try:
        user_query = get_last_user_text(state["messages"])

        response = llm.invoke([
            SystemMessage(content=PARSER_PROMPT),
            HumanMessage(content=user_query),
        ])

        raw = response.content.strip()
        data = extract_json(raw)
        parsed = sanitize_parsed(data, user_query=user_query)

        return {
            **state,
            "parsed": parsed,
        }

    except json.JSONDecodeError:
        return {
            **state,
            "error": "GigaChat вернул невалидный JSON в parse_query_node",
        }
    except ValidationError as e:
        return {
            **state,
            "error": f"JSON не прошёл валидацию: {e}",
        }
    except Exception as e:
        return {
            **state,
            "error": f"Ошибка parse_query_node: {e}",
        }


def embed_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    parsed = state["parsed"]
    vec = emb.embed_query(parsed["embedding_text"])
    return {**state, "embedding": vec}


def agent_call_tool_node(state: AgentState) -> AgentState:
    """
    Создает AIMessage, который вызывает инструмент поиска с подготовленными аргументами.
    """
    if state.get("error"):
        return state

    parsed = state["parsed"]
    tool_args = {
        "text_query": parsed["text_query"],
        "embedding": state.get("embedding") or [],
        "top_k": parsed["top_k"],
    }

    msg = AIMessage(
        content="search",
        tool_calls=[{"name": "search_images", "args": tool_args, "id": f"call_search_images_{uuid.uuid4().hex}"}],
    )
    return {**state, "messages": [*state.get("messages", []), msg]}


def extract_results_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    results: List[Dict[str, Any]] = []
    for m in reversed(state.get("messages", [])):
        if isinstance(m, ToolMessage) and getattr(m, "name", None) == "search_images":
            content = m.content
            if isinstance(content, str):
                try:
                    results = json.loads(content)
                except Exception:
                    results = []
            elif isinstance(content, list):
                results = content  # type: ignore[assignment]
            break

    return {**state, "search_results": results}


def answer_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {
            **state,
            "final_answer": state["error"],
        }

    results = state.get("search_results", [])
    answer = f"Найдено результатов: {len(results)}."
    if results:
        lines: List[str] = []
        for r in results[: min(5, len(results))]:
            doc_id = r.get("document_id") or r.get("doc_id") or ""
            desc = r.get("scene_description") or ""
            fname = r.get("filename") or ""
            chunk = " — ".join([x for x in [str(doc_id), str(fname), str(desc)] if x])
            lines.append(chunk)
        if lines:
            answer += "\n" + "\n".join(lines)

    return {
        **state,
        "final_answer": answer,
    }


def build_graph(store: Store):

    @tool("search_images")
    def search_images(text_query: str, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск (полнотекстовый и векторный) по описанию сцены `scene_description`.
        Возвращает список документов (dict).
        """
        return store.search({"text_query": text_query, "embedding": embedding, "top_k": top_k})

    tools = [search_images]
    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)

    graph.add_node("parse_query", parse_query_node)
    graph.add_node("embed", embed_node)
    graph.add_node("agent", agent_call_tool_node)
    graph.add_node("tools", tool_node)
    graph.add_node("extract_results", extract_results_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("parse_query")
    graph.add_edge("parse_query", "embed")
    graph.add_edge("embed", "agent")
    graph.add_edge("agent", "tools")
    graph.add_edge("tools", "extract_results")
    graph.add_edge("extract_results", "answer")
    graph.add_edge("answer", END)

    return graph.compile()

