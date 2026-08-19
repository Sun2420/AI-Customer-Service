from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=3, max_length=100)
    user_id: str = Field(default="demo-user", min_length=3, max_length=100)


class Source(BaseModel):
    title: str
    score: float
    snippet: str


class ToolTrace(BaseModel):
    name: str
    status: Literal["success", "pending_confirmation", "rejected", "error"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    intent: str
    route: str
    sources: list[Source] = Field(default_factory=list)
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    confirmation_token: str | None = None
    session_summary: str = ""


class RefundConfirmRequest(BaseModel):
    confirmation_token: str
    session_id: str
    user_id: str = "demo-user"
    confirmed: bool


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str | None = None
    rating: Literal[-1, 1]
    comment: str = Field(default="", max_length=500)

