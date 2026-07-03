from __future__ import annotations

import requests

from ..config import settings


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def complete(self, prompt: str) -> str:
        if not self.configured:
            raise RuntimeError("LLM is not configured. Set LLM_API_KEY and LLM_MODEL.")

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个只输出 JSON 的招聘简历解析助手。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
