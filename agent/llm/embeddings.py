import os

from langchain_gigachat.embeddings import GigaChatEmbeddings

from dotenv import load_dotenv

load_dotenv()

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_CORP")


def get_embeddings():
    return GigaChatEmbeddings(
        credentials=GIGACHAT_API_KEY,
        scope=GIGACHAT_SCOPE,
        verify_ssl_certs=False,
    )


if __name__ == "__main__":
    embeddings = get_embeddings()
    print(embeddings.embed_query("работник"))