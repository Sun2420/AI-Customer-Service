import re
from pathlib import Path

from .config import Settings
from .knowledge import BgeM3FaissRetriever, LexicalRetriever, load_documents
from .llm import OpenAICompatibleLLM
from .memory import MemoryStore
from .models import ChatResponse, Source, ToolTrace
from .tools import ToolRegistry


class CustomerServiceAgent:
    def __init__(self, settings: Settings, memory: MemoryStore, tools: ToolRegistry):
        self.settings = settings
        self.memory = memory
        self.tools = tools
        self.llm = OpenAICompatibleLLM(settings)
        docs = load_documents(Path(__file__).parent / "data" / "knowledge.json")
        if settings.embedding_provider.lower() == "bge-m3":
            self.retriever = BgeM3FaissRetriever(docs, settings.embedding_model)
        else:
            self.retriever = LexicalRetriever(docs)

    @staticmethod
    def classify(message: str) -> str:
        text = message.lower()
        if any(k in text for k in ("退款", "退货", "不要了")):
            return "refund"
        if any(k in text for k in ("物流", "快递", "到哪", "运单")):
            return "logistics"
        if any(k in text for k in ("订单", "下单", "购买记录")):
            return "order"
        return "faq"

    def chat(self, message: str, session_id: str, user_id: str) -> ChatResponse:
        history = self.memory.get(session_id)
        analysis = None
        try:
            analysis = self.llm.analyze(message, history)
        except Exception:
            # Model routing must not take down customer service; deterministic routing remains available.
            analysis = None
        self.memory.append(session_id, "user", message)
        intent = analysis["intent"] if analysis else self.classify(message)
        order_id = (analysis.get("order_id") if analysis else None) or self.tools.extract_order_id(message)
        rewritten_query = analysis.get("rewritten_query", message) if analysis else self._rewrite_query(message, history)
        traces: list[ToolTrace] = []
        sources: list[Source] = []
        token = None

        if intent in {"order", "logistics", "refund"} and not order_id:
            answer = "请提供订单号（示例：ORD-20260801），我会在校验订单归属后继续处理。"
            route = "clarification"
        elif intent == "order":
            result = self.tools.order_query(user_id, order_id or "")
            traces.append(ToolTrace(name="order_query", status="success", arguments={"order_id": order_id}, result=result))
            if result["found"]:
                order = result["order"]
                answer = f"订单 {order['order_id']}：{order['product_name']}，金额 ¥{order['amount']:.2f}，状态为{order['status']}。"
            else:
                answer = "未找到该订单，或订单不属于当前账号。为保护隐私，我无法展示其他用户的订单。"
            route = "tool"
        elif intent == "logistics":
            result = self.tools.logistics_query(user_id, order_id or "")
            traces.append(ToolTrace(name="logistics_query", status="success", arguments={"order_id": order_id}, result=result))
            answer = (f"订单 {order_id} 由{result['carrier']}承运，运单号 {result['tracking_no']}。{result['latest']}。"
                      if result.get("found") else "未找到该订单的物流信息，或订单不属于当前账号。")
            route = "tool"
        elif intent == "refund":
            reason = re.sub(r"ORD-[A-Z0-9]+", "", message, flags=re.I).strip() or "用户申请退款"
            try:
                pending = self.tools.request_refund(user_id, order_id or "", reason)
                token = pending.token
                result = {"order_id": pending.order_id, "reason": pending.reason, "expires_in": 300}
                traces.append(ToolTrace(name="refund_apply", status="pending_confirmation", arguments=result, result={}))
                answer = f"即将为订单 {pending.order_id} 申请退款，原因：{pending.reason}。这是有资金影响的操作，请在 5 分钟内确认。"
            except ValueError as exc:
                traces.append(ToolTrace(name="refund_apply", status="rejected", arguments={"order_id": order_id}, result={"error": str(exc)}))
                answer = str(exc)
            route = "tool"
        else:
            sources = self.retriever.search(rewritten_query, self.settings.top_k)
            if sources and sources[0].score >= 0.2:
                evidence = sources[0].snippet
                answer = f"根据帮助中心：{evidence}"
            else:
                answer = "目前知识库中没有足够信息回答这个问题。为了避免误导，我建议转接人工客服。"
            route = "rag"

        self.memory.append(session_id, "assistant", answer)
        return ChatResponse(
            answer=answer,
            intent=intent,
            route=route,
            sources=sources[: self.settings.rerank_top_k],
            tool_trace=traces,
            confirmation_token=token,
            session_summary=self.memory.summary(session_id),
        )

    @staticmethod
    def _rewrite_query(message: str, history: list[dict[str, str]]) -> str:
        """Offline fallback: attach the last user topic when the new question contains a pronoun."""
        if any(word in message for word in ("它", "这个", "那它", "多久呢", "怎么办")):
            previous = next((item["content"] for item in reversed(history) if item["role"] == "user"), "")
            if previous:
                return previous + "；追问：" + message
        return message
