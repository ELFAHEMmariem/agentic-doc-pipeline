"""Factory LLM (Groq) avec retry/backoff — mutualisée par tous les agents."""
from functools import lru_cache

from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import get_settings


@lru_cache
def get_llm(temperature: float | None = None) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature if temperature is not None else settings.groq_temperature,
        max_retries=0,  # on gère le retry nous-mêmes (tenacity) pour logguer/tracer proprement
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
)
def invoke_with_retry(llm, messages):
    """Appel LLM avec backoff exponentiel (rate limit / erreurs réseau Groq)."""
    return llm.invoke(messages)
