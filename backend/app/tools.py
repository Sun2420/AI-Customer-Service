import hashlib
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any

from .repository import Repository


ORDER_RE = re.compile(r"ORD-[A-Z0-9]+", re.I)


@dataclass
class PendingRefund:
    token: str
    order_id: str
    user_id: str
    reason: str
    expires_at: float


class ToolRegistry:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.pending: dict[str, PendingRefund] = {}

    @staticmethod
    def extract_order_id(message: str) -> str | None:
        match = ORDER_RE.search(message)
        return match.group(0).upper() if match else None

    def order_query(self, user_id: str, order_id: str) -> dict[str, Any]:
        order = self.repository.get_order(order_id, user_id)
        return {"found": bool(order), "order": order}

    def logistics_query(self, user_id: str, order_id: str) -> dict[str, Any]:
        order = self.repository.get_order(order_id, user_id)
        if not order:
            return {"found": False}
        return {
            "found": True,
            "order_id": order_id,
            "carrier": order["carrier"],
            "tracking_no": order["tracking_no"],
            "latest": "包裹已到达杭州转运中心，预计明日送达",
        }

    def request_refund(self, user_id: str, order_id: str, reason: str) -> PendingRefund:
        order = self.repository.get_order(order_id, user_id)
        if not order:
            raise ValueError("订单不存在或不属于当前用户")
        if order["status"] not in {"已发货", "已完成"}:
            raise ValueError("当前订单状态不支持退款")
        token = secrets.token_urlsafe(24)
        pending = PendingRefund(token, order_id, user_id, reason, time.time() + 300)
        self.pending[token] = pending
        return pending

    def confirm_refund(self, token: str, user_id: str, confirmed: bool) -> dict[str, Any]:
        pending = self.pending.get(token)
        if not pending or pending.expires_at < time.time():
            raise ValueError("确认请求不存在或已过期")
        if pending.user_id != user_id:
            raise PermissionError("无权确认该退款")
        if not confirmed:
            self.pending.pop(token, None)
            return {"status": "已取消"}
        order = self.repository.get_order(pending.order_id, user_id)
        if not order:
            raise ValueError("订单不存在或不属于当前用户")
        idem = hashlib.sha256(f"{user_id}:{pending.order_id}:{pending.reason}".encode()).hexdigest()
        refund = self.repository.create_refund(order, pending.reason, idem)
        self.pending.pop(token, None)
        return refund

