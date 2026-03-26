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
    profile_picture_url: str | None = None
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    connections_count: int | None = None
    shared_connections_count: int | None = None
    is_premium: bool = False
    websites: list[str] = []


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
    """Dados do lead vinculado ou contato Unipile."""
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
    # Dados do contato Unipile (sempre preenchidos, mesmo sem lead)
    attendee_name: str | None = None
    attendee_profile_url: str | None = None
    attendee_profile_picture_url: str | None = None
    attendee_id: str | None = None
    attendee_headline: str | None = None
    attendee_location: str | None = None
    attendee_email: str | None = None
    attendee_connections_count: int | None = None
    attendee_shared_connections_count: int | None = None
    attendee_is_premium: bool = False
    attendee_websites: list[str] = []


class QuickCreateLeadRequest(BaseModel):
    """Criar lead rápido a partir de contato do inbox."""
    name: str = Field(..., min_length=1, max_length=300)
    linkedin_url: str | None = None
    linkedin_profile_id: str | None = None
    company: str | None = None
    job_title: str | None = None


class AddReactionRequest(BaseModel):
    """Adicionar/remover reação a uma mensagem."""
    emoji: str = Field(..., min_length=1, max_length=10)


# ── Atividade recente do lead ─────────────────────────────────────────

class RecentActivityItem(BaseModel):
    """Uma interação recente com o lead."""
    id: uuid.UUID
    channel: str
    direction: str
    content_preview: str | None = None
    intent: str | None = None
    created_at: datetime


class RecentActivityResponse(BaseModel):
    """Últimas interações do lead."""
    items: list[RecentActivityItem]


# ── Histórico de cadências do lead ────────────────────────────────────

class CadenceHistoryItem(BaseModel):
    """Cadência em que o lead participou/participa."""
    cadence_id: uuid.UUID
    cadence_name: str
    mode: str
    total_steps: int
    completed_steps: int
    last_step_at: datetime | None = None
    is_active: bool


class CadenceHistoryResponse(BaseModel):
    """Lista de cadências do lead."""
    items: list[CadenceHistoryItem]


# ── Tags do lead ──────────────────────────────────────────────────────

class LeadTagSchema(BaseModel):
    """Tag associada a um lead."""
    id: uuid.UUID
    name: str
    color: str


class AddTagRequest(BaseModel):
    """Adicionar tag a um lead."""
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6366f1", max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
