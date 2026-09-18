import os

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    from src.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
