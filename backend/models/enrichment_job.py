"""
models/enrichment_job.py

Model EnrichmentJob — fila de enriquecimento em lote de perfis LinkedIn.

Responsabilidades:
  - Armazena uma lista de URLs do LinkedIn a enriquecer
  - Divide automaticamente em batches (default: 50 URLs por vez)
  - Status: pending → running → done | failed
  - Associa os leads enriquecidos a uma LeadList alvo

O worker process_enrichment_batch (workers/enrichment_queue.py) processa um
batch por execução a cada hora via Celery Beat.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from models.lead_list import LeadList


class EnrichmentJob(Base, TenantMixin, TimestampMixin):
    """
    Fila de enriquecimento de perfis LinkedIn em batches automáticos.
    """

    __tablename__ = "enrichment_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    target_list_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_lists.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lista completa de URLs a processar
    linkedin_urls: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )

    # Quantas URLs processar por batch (padrão: 50)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Ponteiro de progresso: próximo batch começa em processed_count
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Total de URLs enviadas (cached para não recalcular len(linkedin_urls))
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # pending | running | done | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos
    target_list: Mapped["LeadList | None"] = relationship(
        "LeadList", foreign_keys=[target_list_id], lazy="selectin"
    )

    @property
    def progress_pct(self) -> int:
        if self.total_count == 0:
            return 0
        return round(self.processed_count / self.total_count * 100)

    @property
    def remaining_count(self) -> int:
        return max(0, self.total_count - self.processed_count)

    @property
    def batches_remaining(self) -> int:
        import math
        return math.ceil(self.remaining_count / self.batch_size)
