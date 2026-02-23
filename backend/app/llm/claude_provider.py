from __future__ import annotations

import json
from typing import Any

import anthropic

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_user_prompt,
)


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract_requirements(self, transcript_text: str) -> dict[str, Any]:
        response = await self.client.messages.create(
            model=self._model,
            max_tokens=8096,
            temperature=settings.llm_temperature,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": build_extraction_user_prompt(transcript_text),
                }
            ],
        )
        raw_text = response.content[0].text
        return self._parse_json_response(raw_text)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self._model,
            max_tokens=8096,
            temperature=settings.llm_temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())
