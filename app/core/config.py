from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ES_HOST: str = "http://localhost:9200"
    ES_REPLICAS: int = 0
    ES_SHARDS: int = 1

    class Config:
        env_file = ".env"

settings = Settings()