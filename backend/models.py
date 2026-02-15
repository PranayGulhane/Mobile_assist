from pydantic import BaseModel
from typing import Optional


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class Conversation(BaseModel):
    id: str
    title: str
    status: str
    sentiment: str
    ticket_id: Optional[str] = None
    ticket_type: str
    resolution_status: str
    messages: list[ConversationMessage]
    created_at: str
    summary: Optional[str] = None
    escalated: bool = False


class TextQueryRequest(BaseModel):
    conversation_id: str
    message: str


class CreateTicketRequest(BaseModel):
    conversation_id: str
    title: str
    description: str
    ticket_type: str
    sentiment: str
    escalated: bool
    resolution_status: str


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float
    details: str
