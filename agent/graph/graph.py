import json
import uuid
import asyncio
from typing import Any, Dict, List, Protocol, runtime_checkable

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


@runtime_checkable
class Store(Protocol):
    def search(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]: ...

    async def asearch(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]: ...


def get_last_user_text(messages: List[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    raise ValueError("Не найдено сообщение пользователя")


def sanitize_parsed(parsed: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    intent = str(parsed.get("intent") or "search").strip().lower()
    if intent not in {"chat", "search"}:
        intent = "search"

    if intent == "chat":
        return {
            "intent": "chat",
            "text_query": "",
            "embedding_text": "",
            "top_k": 0,
        }

    text_query = str(parsed.get("text_query") or user_query).strip()
    embedding_text = str(parsed.get("embedding_text") or text_query).strip()
    try:
        top_k = int(parsed.get("top_k") or 5)
    except Exception:
        top_k = 5
    top_k = max(1, min(top_k, 20))

    return {
        "intent": "search",
        "text_query": text_query,
        "embedding_text": embedding_text,
        "top_k": top_k,
    }

def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("JSON object not found", text, 0)
    return json.loads(text[start:end + 1])

def clean_user_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
    return text.strip()

def route_after_parse(state: AgentState) -> str:
    if state.get("error"):
        return "answer"

    parsed = state.get("parsed") or {}
    intent = parsed.get("intent", "search")
    if intent == "chat":
        return "answer"
    return "embed"


async def parse_query_node(state: AgentState) -> AgentState:
    try:
        user_query = clean_user_text(get_last_user_text(state["messages"]))

        response = await llm.ainvoke([
            SystemMessage(content=PARSER_PROMPT),
            HumanMessage(content=user_query),
        ])

        raw = str(response.content).strip()
        data = extract_json(raw)
        parsed = sanitize_parsed(data, user_query=user_query)

        return {
            **state,
            "parsed": parsed,
            "user_query": user_query,
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
        # Some exceptions may contain unpaired surrogates; keep error message printable.
        safe = (repr(e)).encode("utf-8", "backslashreplace").decode("utf-8", "strict")
        return {
            **state,
            "error": f"Ошибка parse_query_node: {safe}",
        }


async def embed_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    parsed = state["parsed"]
    embedding_text = parsed["embedding_text"]

    aembed_query = getattr(emb, "aembed_query", None)
    if callable(aembed_query):
        vec = await aembed_query(embedding_text)
    else:
        vec = await asyncio.to_thread(emb.embed_query, embedding_text)
    return {**state, "embedding": vec}


async def agent_call_tool_node(state: AgentState) -> AgentState:
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


async def extract_results_node(state: AgentState) -> AgentState:
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


async def answer_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return {
            **state,
            "final_answer": state["error"],
        }

    parsed = state.get("parsed") or {}
    intent = parsed.get("intent", "search")
    user_query = clean_user_text(state.get("user_query", ""))

    if not user_query:
        return {
            **state,
            "final_answer": "Не удалось получить текст пользовательского запроса.",
        }

    if intent == "chat":
        response = await llm.ainvoke([
            SystemMessage(content=(
                "Ты помощник по поиску информации по изображениям с видеокамер. "
                "Если пользователь здоровается или задает общий вопрос, отвечай дружелюбно и кратко. "
                "Объясняй, что ты умеешь искать информацию по текстовым описаниям сцен на изображениях."
            )),
            HumanMessage(content=user_query),
        ])
        return {
            **state,
            "final_answer": str(response.content).strip(),
        }

    results = state.get("search_results", [])
    if not results:
        return {
            **state,
            "final_answer": "По найденным описаниям я не вижу подтверждения.",
        }

    context_lines = []
    for i, r in enumerate(results[:5], 1):
        doc_id = r.get("document_id") or ""
        desc = r.get("scene_description") or ""
        context_lines.append(f"{i}. [{doc_id}] {desc}")

    prompt = f"""
        Ответь на вопрос пользователя только на основе найденных описаний сцен.
        Не выдумывай факты.
        Если данных недостаточно, так и скажи.
        Если ответ положительный, скажи это прямо и можешь сослаться на найденные кадры.

        Вопрос пользователя:
        {user_query}

        Найденные описания:
        {chr(10).join(context_lines)}
        """.strip()

    response = await llm.ainvoke([
        SystemMessage(content="Ты помощник по анализу описаний сцен с камер. Отвечай кратко и по делу."),
        HumanMessage(content=prompt),
    ])

    return {
        **state,
        "final_answer": str(response.content).strip(),
    }


def build_graph(store: Store):

    def route_after_agent(state: AgentState) -> str:
        # If we already have an error, don't enter ToolNode (it requires an AIMessage).
        return "answer" if state.get("error") else "tools"

    @tool("search_images")
    async def search_images(text_query: str, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск (полнотекстовый и векторный) по описанию сцены `scene_description`.
        Возвращает список документов (dict).
        """
        payload = {"text_query": text_query, "embedding": embedding, "top_k": top_k}
        asearch = getattr(store, "asearch", None)
        if callable(asearch):
            return await asearch(payload)
        return await asyncio.to_thread(store.search, payload)

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
    graph.add_conditional_edges(
        "parse_query",
        route_after_parse,
        {
            "embed": "embed",
            "answer": "answer",
        },
    )
    graph.add_edge("embed", "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "answer": "answer"})
    graph.add_edge("tools", "extract_results")
    graph.add_edge("extract_results", "answer")
    graph.add_edge("answer", END)

    return graph.compile()

