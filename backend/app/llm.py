import json
from typing import Any

import httpx

from .config import Settings


INTENT_SCHEMA = {
    "name": "customer_service_intent",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": ["faq", "order", "logistics", "refund"]},
            "order_id": {"type": ["string", "null"]},
            "reason": {"type": ["string", "null"]},
            "rewritten_query": {"type": "string"},
        },
        "required": ["intent", "order_id", "reason", "rewritten_query"],
        "additionalProperties": False,
    },
}


class OpenAICompatibleLLM:
    """Qwen/OpenAI-compatible adapter for structured intent and query rewrite."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return not self.settings.demo_mode and bool(self.settings.llm_api_key)

    def analyze(self, message: str, history: list[dict[str, str]]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        prompt = (
            "你是电商客服路由器。根据对话识别意图，抽取订单号和退款原因，并把省略指代改写成"
            "可独立检索的查询。不得虚构订单号。只输出符合 JSON Schema 的对象。"
        )
        payload = {
            "model": self.settings.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                *history[-6:],
                {"role": "user", "content": message},
            ],
            "response_format": {"type": "json_schema", "json_schema": INTENT_SCHEMA},
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        with httpx.Client(timeout=20) as client:
            response = client.post(
                self.settings.llm_base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

