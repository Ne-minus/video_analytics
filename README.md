# video_analytics

# Предлагаемая структура приложения (см структуру папок)

Чуть чуть набросал вам:
- докерфайл в каждой папке
- docker-compose.yml

Остальные файлы пустые

Корневая папка общая

В каждом собираемом в отдельный образ модуле - по отдельному dockerfile

в img2vlm - ручка для загрузки картинки

## Simple agent (Elastic + embeddings)

Пайплайн агента:
`user query → JSON(text_query, embedding_text, top_k) → gigachat_embeddings → ElasticSearch`.

### Config

- **Select backend**: `SEARCH_BACKEND=memory|elastic` (default: `memory`)
- **Elastic**:
  - `ELASTIC_URL` (default: `http://localhost:9200`)
  - `ELASTIC_INDEX` (default: `images`)
  - `ELASTIC_TEXT_FIELD` (default: `scene_description`)
  - `ELASTIC_VECTOR_FIELD` (default: `scene_embedding`)

### Run (CLI)

```bash
pip install -r requirements.txt
python -m test_graph
```
