# FastAPI сервис: VLM -> Kafka

Сервис принимает изображения по HTTP или читает ссылки на изображения из Kafka, забирает файлы из S3, отправляет их в VLM и публикует результат в Kafka-топик `output`.

## Что внутри

- `POST /describe-and-index` — принимает изображение, вызывает VLM и кладёт результат в Kafka.
- Kafka consumer `imgs_to_process` — читает из Kafka ссылки на файлы в S3, забирает изображения из S3, прогоняет через VLM и кладёт результат в `output`.
- `image-simulator` — отдельный сервис, который читает локальную папку с изображениями, раз в 3 секунды загружает очередную картинку в S3 и публикует в `imgs_to_process` только ссылку на объект.
- MinIO — локальное S3-compatible хранилище для изображений.
- `GET /health` — проверка состояния Kafka и S3.

## Выходной контракт

Результат публикуется в Kafka-топик `output`. Внешний consumer может читать его на своей стороне.

Пример сообщения:

```json
{
  "document_id": "8ec7d6c8-52d4-4b0f-9cc1-1d8f5e5de1f3",
  "filename": "example.jpg",
  "content_type": "image/jpeg",
  "people_analysis": {
    "people_count": 3,
    "people_present": true,
    "people_summary": "На изображении видны три человека на среднем плане."
  },
  "scene_description": "На изображении городская сцена: три человека идут по улице рядом с припаркованными машинами и зданиями на заднем плане.",
  "metadata": {
    "source": "dataset-simulator"
  },
  "created_at": "2026-04-06T10:00:00+00:00"
}
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Ключевые переменные:

- `GIGACHAT_API_KEY` — ключ для GigaChat
- `GIGACHAT_MODEL` — модель GigaChat
- `GIGACHAT_PEOPLE_PROMPT` — prompt для JSON с количеством людей
- `GIGACHAT_SCENE_PROMPT` — prompt для общего описания сцены
- `KAFKA_BOOTSTRAP_SERVERS` — адрес Kafka
- `KAFKA_INPUT_TOPIC` — топик с входными изображениями
- `KAFKA_OUTPUT_TOPIC` — топик, куда пишется результат VLM
- `KAFKA_INPUT_CONSUMER_GROUP` — consumer group для обработки изображений
- `SIMULATOR_INTERVAL_SECONDS` — интервал публикации картинок в Kafka
- `SIMULATOR_DATASET_DIR` — локальная директория, из которой simulator читает изображения
- `S3_ENDPOINT_URL` — адрес S3/MinIO
- `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` — доступ к S3
- `S3_BUCKET_NAME` — bucket с изображениями

## Запуск

```bash
docker compose up --build
```

После старта `image-simulator` будет брать изображения из `SIMULATOR_DATASET_DIR`, загружать их в S3 и публиковать ссылки на них в `imgs_to_process` каждые 3 секунды.

## Пример запроса

```bash
curl -X POST http://localhost:8000/describe-and-index \
  -F "file=@./example.jpg" \
  -F 'metadata_json={"source":"demo","category":"test"}'
```

Ответ:

```json
{
  "status": "ok",
  "document_id": "8ec7d6c8-52d4-4b0f-9cc1-1d8f5e5de1f3",
  "kafka_topic": "output",
  "people_analysis": {
    "people_count": 3,
    "people_present": true,
    "people_summary": "На изображении видны три человека."
  },
  "scene_description": "Подробное описание сцены...",
  "kafka_result": "queued"
}
```

## GigaChat

Сервис работает только через GigaChat: сначала загружает изображение в хранилище GigaChat, затем делает два вызова `chat` с `attachments` для одной и той же картинки.

Первый вызов возвращает строго JSON:

- `people_analysis` — структурированные данные о наличии и количестве людей

Второй вызов возвращает:

- `scene_description` — подробное текстовое описание сцены в 5-7 предложениях

Входной Kafka-поток содержит ссылку на изображение в S3, а результат публикуется в Kafka-топик `output`, который может читать внешний потребитель.

## Источник изображений для симулятора

Симулятор ничего не скачивает сам. Он читает любые изображения из локальной директории `SIMULATOR_DATASET_DIR` и отправляет их по кругу.

Поддерживаются файлы:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

# video_analytics