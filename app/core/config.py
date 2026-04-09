from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    # <--- Конфиг ElasticSearch --->
    ES_HOST: str = "http://localhost:9200"
    ES_REPLICAS: int = 0
    ES_SHARDS: int = 1
    ES_VECTOR_SIZE: int = 1024

    # <--- Конфиг Kafka (read-only) --->
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUME_TOPIC: str = "imgs_descriptions"
    KAFKA_CONSUMER_GROUP: str = "elastic-indexer"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = True

    # <--- Гигачат --->
    GIGACHAT_BASE_URL: str = "https://gigachat.devices.sberbank.ru/api/v1"
    GIGACHAT_API_KEY: str = "Y2ZhOTI0Y2ItZGE2Ni00NTRlLWE2YWEtMDJkYWU3ZTgyZGMwOmQ1MDRlMWU5LTc1ZDctNDE1Yy1iMDRjLTExMTY5MTc0YzkzMg=="
    GIGACHAT_SCOPE: str = "GIGACHAT_API_CORP"
    CLIENT_ID: str = "cfa924cb-da66-454e-a6aa-02dae7e82dc0"
    CLIENT_SECRET: str = "d504e1e9-75d7-415c-b04c-11169174c932"

    # <--- .env --->
    class Config:
        env_file = ".env"

settings = Settings()