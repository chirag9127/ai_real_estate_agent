from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def extract_requirements(self, transcript_text: str) -> dict[str, Any]: ...

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...
