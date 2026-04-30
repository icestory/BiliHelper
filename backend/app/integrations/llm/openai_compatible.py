"""OpenAI 兼容接口的 LLM Provider 实现"""
import json
import re
from typing import Any

import httpx

from app.integrations.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None, default_model: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.default_model = default_model or "gpt-4o-mini"

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body: dict = {
            "model": model or self.default_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        # response_format 仅对 openai 系 provider 启用
        if not self.base_url or "openai.com" in self.base_url or "/v1" in (self.base_url or ""):
            body["response_format"] = {"type": "json_object"}

        resp = httpx.post(url, headers=headers, json=body, timeout=120)
        resp.raise_for_status()

        data = resp.json()
        # 防御性检查：API 可能返回异常结构
        if "choices" not in data or len(data["choices"]) == 0:
            raise ValueError(f"LLM API 返回异常: choices 为空 — {str(data)[:200]}")
        if "message" not in data["choices"][0] or "content" not in data["choices"][0]["message"]:
            raise ValueError(f"LLM API 返回异常: 缺少 message/content — {str(data)[:200]}")
        content = data["choices"][0]["message"]["content"]
        if content is None:
            raise ValueError("LLM 返回 content 为 null")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试从 markdown code block 中提取 JSON
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"LLM 返回内容无法解析为 JSON: {content[:200]}")
