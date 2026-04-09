from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ES_HOST: str = "http://localhost:9200"
    ES_REPLICAS: int = 0
    ES_SHARDS: int = 1
    ES_VECTOR_DIMS: int = 384

    class Config:
        env_file = ".env"

settings = Settings()