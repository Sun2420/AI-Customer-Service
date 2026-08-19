from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .agent import CustomerServiceAgent
from .config import get_settings
from .memory import MemoryStore
from .models import ChatRequest, ChatResponse, FeedbackRequest, RefundConfirmRequest, ToolTrace
from .repository import Repository
from .tools import ToolRegistry


settings = get_settings()
repository = Repository(settings.sqlite_path)
memory = MemoryStore(settings.redis_url, settings.session_ttl_seconds, settings.max_history_messages)
tools = ToolRegistry(repository)
agent = CustomerServiceAgent(settings, memory, tools)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "mode": "demo" if settings.demo_mode else "production"}


@app.get(f"{settings.api_prefix}/demo")
def demo_data():
    return {
        "user_id": "demo-user",
        "orders": ["ORD-20260801", "ORD-20260802"],
        "examples": ["会员积分多久过期？", "查询订单 ORD-20260801", "ORD-20260801 物流到哪了？", "订单 ORD-20260802 申请退款，不想要了"],
    }


@app.post(f"{settings.api_prefix}/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    return agent.chat(payload.message, payload.session_id, payload.user_id)


@app.post(f"{settings.api_prefix}/refund/confirm", response_model=ChatResponse)
def refund_confirm(payload: RefundConfirmRequest):
    try:
        result = tools.confirm_refund(payload.confirmation_token, payload.user_id, payload.confirmed)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    answer = (f"退款申请已提交，退款单号 {result['refund_id']}，当前状态：{result['status']}。"
              if payload.confirmed else "已取消本次退款申请。")
    memory.append(payload.session_id, "assistant", answer)
    return ChatResponse(
        answer=answer,
        intent="refund_confirmation",
        route="tool",
        tool_trace=[ToolTrace(name="refund_confirm", status="success", arguments={"confirmed": payload.confirmed}, result=result)],
        session_summary=memory.summary(payload.session_id),
    )


@app.delete(f"{settings.api_prefix}/sessions/{{session_id}}")
def clear_session(session_id: str):
    memory.clear(session_id)
    return {"cleared": True}


@app.post(f"{settings.api_prefix}/feedback")
def feedback(payload: FeedbackRequest):
    repository.add_feedback(payload.session_id, payload.message_id, payload.rating, payload.comment)
    return {"saved": True}

