from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: int | None = None
    max_tokens: int = Field(default=512, ge=1, le=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return value


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    timestamp: datetime


class MemoryOut(BaseModel):
    id: int
    user_id: str
    memory_text: str
    importance: float
    created_at: datetime


class UserOut(BaseModel):
    id: str
    email: str
    name: str | None = None
