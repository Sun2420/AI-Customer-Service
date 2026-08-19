from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "SmartCare Agent"
    demo_mode: bool = True
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/customer_service.db"
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86400
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5-7b-instruct"
    embedding_provider: str = "lexical"
    embedding_model: str = "BAAI/bge-m3"
    top_k: int = 5
    rerank_top_k: int = 3
    max_history_messages: int = 10

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        raw = self.database_url[len(prefix):] if self.database_url.startswith(prefix) else "./data/customer_service.db"
        return Path(raw).expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()

