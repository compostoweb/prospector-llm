"""
schemas/inbox.py

Schemas Pydantic v2 para a UniBox LinkedIn (conversas/chat).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.enums import LeadStatus


class ChatAttendeeSchema(BaseModel):
    """Participante de uma conversa."""
    id: str
    name: str
    profile_url: str | None = None


class ConversationSchema(BaseModel):
    """Conversa na listagem do inbox."""
    chat_id: str
    attendees: list[ChatAttendeeSchema] = []
    last_message_text: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0
    # Lead vinculado (se existir no sistema)
    has_lead: bool = False
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    lead_company: str | None = None
    lead_status: LeadStatus | None = None


class ConversationListResponse(BaseModel):
    """Lista paginada de conversas."""
    items: list[ConversationSchema]
    cursor: str | None = None


class ChatMessageSchema(BaseModel):
    """Uma mensagem dentro de um chat."""
    id: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: str
    is_own: bool = False
    attachments: list[dict] = []


class ChatMessagesResponse(BaseModel):
    """Lista paginada de mensagens de um chat."""
    items: list[ChatMessageSchema]
    cursor: str | None = None


class SendMessageRequest(BaseModel):
    """Enviar mensagem texto em conversa existente."""
    text: str = Field(..., min_length=1, max_length=5000)


class SuggestReplyRequest(BaseModel):
    """Solicitar sugestão de resposta via LLM."""
    tone: str = Field(
        default="formal",
        description="Tom: formal | casual | objetiva | consultiva",
    )


class SuggestReplyResponse(BaseModel):
    """Sugestão de resposta gerada."""
    suggested_text: str
    tone: str


class ConversationLeadResponse(BaseModel):
    """Dados do lead vinculado a uma conversa."""
    has_lead: bool = False
    lead_id: uuid.UUID | None = None
    name: str | None = None
    company: str | None = None
    job_title: str | None = None
    linkedin_url: str | None = None
    email_corporate: str | None = None
    email_personal: str | None = None
    phone: str | None = None
    city: str | None = None
    segment: str | None = None
    industry: str | None = None
    score: float | None = None
    status: LeadStatus | None = None
    notes: str | None = None
    # Tarefas pendentes do lead
    pending_tasks_count: int = 0
