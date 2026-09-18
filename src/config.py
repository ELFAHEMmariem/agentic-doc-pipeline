"""Configuration centralisée (pydantic-settings) — lit .env une seule fois."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.0

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "sprint2-multi-agent-system"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # Checkpointer
    checkpointer_backend: str = "memory"  # "memory" | "postgres"
    postgres_dsn: str = "postgresql://postgres:postgres@localhost:5432/agentdb"

    # API
    api_key: str = "change-me-in-prod"
    rate_limit_per_minute: int = 30
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_langsmith(settings: Settings) -> None:
    """Exporte les variables d'environnement attendues par le SDK LangChain/LangSmith."""
    import os

    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        if settings.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
