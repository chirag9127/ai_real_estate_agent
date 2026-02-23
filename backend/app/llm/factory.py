from __future__ import annotations

from app.config import settings
from app.llm.base import LLMProvider

_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is None:
        if settings.llm_provider == "claude":
            from app.llm.claude_provider import ClaudeProvider

            _provider_instance = ClaudeProvider()
        elif settings.llm_provider == "openai":
            from app.llm.openai_provider import OpenAIProvider

            _provider_instance = OpenAIProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
    return _provider_instance
