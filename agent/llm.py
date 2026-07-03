from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


dp_base_url = "https://api.deepseek.com"
dp_model = 'deepseek-v4-pro'
dp_api_key = os.environ.get("DEEPSEEK_API_KEY")

class LLMClient(Protocol):
    def invoke(self, messages: list[dict[str, str]]) -> str:
        ...

class OpenAICompatibleLLM:
    def __init__(
        self,
        api_key: str | None = dp_api_key,
        model: str | None = dp_model,
        base_url: str | None = dp_base_url,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")

    def invoke(self, messages: list[dict[str, str]]) -> str:
        body = json.dumps({"model": self.model, "messages": messages, "temperature": 0}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        return data["choices"][0]["message"]["content"]
