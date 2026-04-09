from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "vlm-indexer"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    gigachat_api_key: str = ""
    gigachat_base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    gigachat_model: str = "GigaChat-2-Max"
    gigachat_scene_prompt: str = (
        "Опиши сцену на изображении на русском языке в 5-7 предложениях. "
        "Сначала оцени количество людей в кадре и обязательно явно укажи это в описании. "
        "Если людей нет, прямо напиши, что людей в кадре не видно. "
        "Дальше подробно опиши объекты, окружение, действия и общую обстановку без домыслов. "
        "Если видны двери, укажи их цвет."
    )

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_input_topic: str = "imgs_to_process"
    kafka_output_topic: str = "img_descriptions"
    kafka_input_consumer_group: str = "vlm-image-processor"
    kafka_auto_offset_reset: str = "earliest"
    kafka_start_retries: int = 20
    kafka_retry_delay_seconds: int = 3

    simulator_interval_seconds: int = 3
    simulator_dataset_dir: str = "./sample_data"

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "vlm-images"
    s3_region_name: str = "us-east-1"
    s3_use_ssl: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
