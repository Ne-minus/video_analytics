from langchain_core.messages import HumanMessage
from agent.graph.graph import build_graph
import json
# from ... Store

# store = Store()
app = build_graph(store)
 
while True:
    user_input = input("\nЗапрос: ").strip()
    if user_input.lower() in {"exit", "quit", "q"}:
        break

    result = app.invoke({
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