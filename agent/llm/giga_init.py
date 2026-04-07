from langchain_gigachat.chat_models import GigaChat

import os
from dotenv import load_dotenv

load_dotenv()

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

def get_llm(model=GIGACHAT_MODEL) -> GigaChat:
    giga = GigaChat(
        model=model,
        credentials=GIGACHAT_API_KEY,
        scope=GIGACHAT_SCOPE,
        verify_ssl_certs=False,
        temperature=0.1
    )
    return giga


if __name__ == "__main__":
    giga = get_llm()
    print(giga.invoke("Привет!").content)