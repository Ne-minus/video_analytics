# video_analytics

в img2vlm - ручка для загрузки картинки

## Simple agent (Elastic + embeddings)

Пайплайн агента:
`user query → JSON(text_query, embedding_text, top_k) → gigachat_embeddings → ElasticSearch`.


### Run (CLI)

```bash
pip install -r requirements.txt
python -m agent.app
```
