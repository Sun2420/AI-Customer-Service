import json
from collections import defaultdict
from typing import Any


class MemoryStore:
    def __init__(self, redis_url: str, ttl: int, max_messages: int):
        self.ttl = ttl
        self.max_messages = max_messages
        self.local: dict[str, list[dict[str, str]]] = defaultdict(list)
        self.redis = None
        try:
            import redis
            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=0.2)
            client.ping()
            self.redis = client
        except Exception:
            self.redis = None

    def _key(self, session_id: str) -> str:
        return f"smartcare:session:{session_id}"

    def get(self, session_id: str) -> list[dict[str, str]]:
        if self.redis:
            raw = self.redis.get(self._key(session_id))
            return json.loads(raw) if raw else []
        return list(self.local[session_id])

    def append(self, session_id: str, role: str, content: str) -> None:
        messages = self.get(session_id)
        messages.append({"role": role, "content": content})
        messages = messages[-self.max_messages:]
        if self.redis:
            self.redis.setex(self._key(session_id), self.ttl, json.dumps(messages, ensure_ascii=False))
        else:
            self.local[session_id] = messages

    def summary(self, session_id: str) -> str:
        messages = self.get(session_id)
        if not messages:
            return "暂无会话记忆"
        user_messages = [m["content"] for m in messages if m["role"] == "user"][-3:]
        return "；".join(user_messages)[:180]

    def clear(self, session_id: str) -> None:
        if self.redis:
            self.redis.delete(self._key(session_id))
        self.local.pop(session_id, None)

