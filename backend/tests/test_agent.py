from pathlib import Path

from app.agent import CustomerServiceAgent
from app.config import Settings
from app.memory import MemoryStore
from app.repository import Repository
from app.tools import ToolRegistry


def build_agent(tmp_path: Path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", redis_url="redis://127.0.0.1:1/0")
    repo = Repository(settings.sqlite_path)
    tools = ToolRegistry(repo)
    memory = MemoryStore(settings.redis_url, 60, 10)
    return CustomerServiceAgent(settings, memory, tools), tools


def test_faq_rag(tmp_path):
    agent, _ = build_agent(tmp_path)
    response = agent.chat("会员积分多久过期？", "s-001", "demo-user")
    assert response.route == "rag"
    assert "12 个月" in response.answer
    assert response.sources


def test_order_permission_boundary(tmp_path):
    agent, _ = build_agent(tmp_path)
    response = agent.chat("查询订单 ORD-OTHER001", "s-002", "demo-user")
    assert "不属于当前账号" in response.answer


def test_refund_requires_confirmation_and_is_idempotent(tmp_path):
    agent, tools = build_agent(tmp_path)
    response = agent.chat("订单 ORD-20260802 退款，不想要了", "s-003", "demo-user")
    assert response.confirmation_token
    first = tools.confirm_refund(response.confirmation_token, "demo-user", True)
    response2 = agent.chat("订单 ORD-20260802 退款，不想要了", "s-003", "demo-user")
    second = tools.confirm_refund(response2.confirmation_token, "demo-user", True)
    assert first["refund_id"] == second["refund_id"]


def test_refund_cannot_be_confirmed_by_other_user(tmp_path):
    agent, tools = build_agent(tmp_path)
    response = agent.chat("订单 ORD-20260802 退款", "s-004", "demo-user")
    try:
        tools.confirm_refund(response.confirmation_token, "other-user", True)
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-user confirmation should fail")

