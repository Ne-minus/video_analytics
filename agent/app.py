from langchain_core.messages import HumanMessage
from agent.graph.graph import build_graph
import json
import asyncio
from agent.store.storage_http import StorageHttpStore

store = StorageHttpStore()
app = build_graph(store)
 
async def main() -> None:
    while True:
        user_input = input("\nЗапрос: ").strip()
        if user_input.lower() in {"exit", "quit", "q"}:
            break

        result = await app.ainvoke({
            "messages": [HumanMessage(content=user_input)]
        })

        if result.get("error"):
            print("\nERROR:")
            print(result["error"])
        else:
            print("\nPARSED:")
            print(json.dumps(result.get("parsed"), ensure_ascii=False, indent=2))
            print("\nANSWER:")
            print(result.get("final_answer"))


if __name__ == "__main__":
    asyncio.run(main())