"""
api/routes/admin_users.py

Gerenciamento da allowlist de usuários (acesso ao painel admin).

Todos os endpoints requerem superuser (is_superuser=True).

Endpoints:
  GET    /admin/users           → lista todos os usuários
  POST   /admin/users           → adiciona email à allowlist
  DELETE /admin/users/{user_id} → desativa um usuário (não apaga)

Nota de segurança:
  - O DELETE não remove o registro — apenas seta is_active=False.
    Isso preserva o histórico de acesso e permite reativação futura.
  - Somente o superadmin pode criar/desativar usuários.
  - O superadmin master (SUPERUSER_EMAIL) não pode ser desativado via API.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from core.security import UserPayload, require_superuser
from models.user import User
from schemas.user import UserCreateRequest, UserResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/users", tags=["Admin — Usuários"])


# ── Sessão sem RLS (users não é multi-tenant) ─────────────────────────

async def _get_raw_session():  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ── Listar usuários ───────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse])
async def list_users(
    _admin: UserPayload = Depends(require_superuser),
    db: AsyncSession = Depends(_get_raw_session),
) -> list[UserResponse]:
    """Lista todos os usuários da allowlist (ativos e inativos)."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


# ── Adicionar usuário à allowlist ─────────────────────────────────────

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    admin: UserPayload = Depends(require_superuser),
    db: AsyncSession = Depends(_get_raw_session),
) -> UserResponse:
    """
    Adiciona um email à allowlist.

    O usuário poderá logar via Google OAuth assim que o registro existir.
    O google_sub será preenchido automaticamente no primeiro login.
    """
    email_normalized = body.email.lower().strip()

    # Verifica duplicata
    existing = await db.execute(select(User).where(User.email == email_normalized))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{email_normalized}' já está cadastrado.",
        )

    user = User(
        email=email_normalized,
        name=body.name,
        is_superuser=body.is_superuser,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "admin.user_created",
        email=user.email,
        is_superuser=user.is_superuser,
        created_by=admin.email,
    )
    return UserResponse.model_validate(user)


# ── Desativar usuário ─────────────────────────────────────────────────

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def deactivate_user(
    user_id: uuid.UUID,
    admin: UserPayload = Depends(require_superuser),
    db: AsyncSession = Depends(_get_raw_session),
) -> None:
    """
    Desativa um usuário (revoga o acesso).

    O registro é preservado — use POST /admin/users para reativar
    ou edite diretamente no banco (is_active=True).
    O superadmin master não pode ser desativado.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Protege o superadmin master de ser desativado via API
    if user.email.lower() == settings.SUPERUSER_EMAIL.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O admin master não pode ser desativado via API.",
        )

    user.is_active = False
    await db.commit()

    logger.info(
        "admin.user_deactivated",
        email=user.email,
        deactivated_by=admin.email,
    )
