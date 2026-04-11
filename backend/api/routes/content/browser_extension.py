from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from api.routes.content.engagement import (
    _load_session_or_404,
    _upsert_external_post,
)
from core.config import settings
from core.redis_client import redis_client
from core.security import UserPayload, get_current_user_payload
from models.content_engagement_event import ContentEngagementEvent
from models.content_engagement_session import ContentEngagementSession
from models.content_extension_capture import ContentExtensionCapture
from models.content_linkedin_account import ContentLinkedInAccount
from models.content_reference import ContentReference
from models.user import User
from schemas.browser_extension import (
    BrowserExtensionBootstrapResponse,
    BrowserExtensionCaptureRequest,
    BrowserExtensionCaptureResponse,
    BrowserExtensionFeatureFlags,
    BrowserExtensionImportStatusMatch,
    BrowserExtensionImportStatusRequest,
    BrowserExtensionImportStatusResponse,
    BrowserExtensionLinkedInStatus,
    BrowserExtensionRecentEngagementSession,
    BrowserExtensionUserSummary,
)
from schemas.content_engagement import AddManualPostRequest
from services.browser_extension import ensure_extension_id_allowed
from services.content.engagement_post_identity import build_post_identity

logger = structlog.get_logger()

router = APIRouter(prefix="/extension", tags=["Content Hub — Browser Extension"])

_EXTENSION_PLATFORM = "chrome_extension"
_EXTENSION_CAPTURE_RATE_TTL = 86400


def _extension_feature_flags() -> BrowserExtensionFeatureFlags:
    enabled = settings.EXTENSION_LINKEDIN_CAPTURE_ENABLED
    return BrowserExtensionFeatureFlags(
        capture_reference=enabled,
        capture_engagement=enabled,
    )


def _get_extension_headers(request: Request) -> tuple[str, str | None]:
    platform = request.headers.get("X-Client-Platform", "").strip().lower()
    if platform != _EXTENSION_PLATFORM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisicao exclusiva da extensao do navegador.",
        )

    extension_id_header = request.headers.get("X-Extension-Id", "")
    extension_id = ensure_extension_id_allowed(extension_id_header)
    extension_version = request.headers.get("X-Extension-Version")
    return extension_id, extension_version


async def _load_reference_match(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dedup_key: str | None,
) -> ContentReference | None:
    if not dedup_key:
        return None

    result = await db.execute(
        select(ContentReference).where(ContentReference.tenant_id == tenant_id)
    )
    for reference in result.scalars().all():
        _, reference_dedup_key = build_post_identity(
            post_url=reference.source_url,
            post_text=reference.body,
            author_name=reference.author_name,
        )
        if reference_dedup_key == dedup_key:
            return reference

    return None


def _compute_engagement_score(*, likes: int, comments: int, shares: int) -> int:
    return comments * 3 + likes + shares * 2


def _merge_reference_payload(
    reference: ContentReference, body: BrowserExtensionCaptureRequest
) -> None:
    post = body.post
    if post.author_name and not reference.author_name:
        reference.author_name = post.author_name
    if post.author_title and not reference.author_title:
        reference.author_title = post.author_title
    if post.author_company and not reference.author_company:
        reference.author_company = post.author_company
    if post.post_url and not reference.source_url:
        reference.source_url = post.post_url
    if post.post_text and len(post.post_text) > len(reference.body):
        reference.body = post.post_text

    next_score = _compute_engagement_score(
        likes=post.likes,
        comments=post.comments,
        shares=post.shares,
    )
    if next_score:
        reference.engagement_score = max(reference.engagement_score or 0, next_score)


async def _record_capture_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    destination_type: str,
    result: str,
    source_url: str | None,
    canonical_post_url: str | None,
    dedup_key: str | None,
    linked_object_type: str | None,
    linked_object_id: uuid.UUID | None,
    client_context: dict[str, object],
    captured_payload: dict[str, object],
) -> None:
    db.add(
        ContentExtensionCapture(
            tenant_id=tenant_id,
            user_id=user_id,
            source_platform="linkedin",
            destination_type=destination_type,
            result=result,
            source_url=source_url,
            canonical_post_url=canonical_post_url,
            dedup_key=dedup_key,
            linked_object_type=linked_object_type,
            linked_object_id=linked_object_id,
            client_context=client_context,
            captured_payload=captured_payload,
        )
    )


async def _check_extension_capture_rate_limit(*, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    key = f"extension_capture:{tenant_id}:{user_id}:{datetime.now(UTC).date().isoformat()}"
    current = await redis_client.increment_with_ttl(key, _EXTENSION_CAPTURE_RATE_TTL)
    if current > settings.EXTENSION_CAPTURE_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diario de capturas da extensao atingido para este usuario.",
        )


@router.get("/bootstrap", response_model=BrowserExtensionBootstrapResponse)
async def get_extension_bootstrap(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user_payload: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> BrowserExtensionBootstrapResponse:
    extension_id, extension_version = _get_extension_headers(request)

    user_result = await db.execute(
        select(User).where(User.id == user_payload.user_id, User.is_active.is_(True))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado ou inativo.",
        )

    linkedin_result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
            ContentLinkedInAccount.is_active.is_(True),
        )
    )
    linkedin_account = linkedin_result.scalar_one_or_none()

    session_result = await db.execute(
        select(ContentEngagementSession)
        .where(
            ContentEngagementSession.tenant_id == tenant_id,
            ContentEngagementSession.status != "failed",
            ContentEngagementSession.error_message.is_(None),
        )
        .order_by(ContentEngagementSession.created_at.desc())
        .limit(10)
    )
    sessions = session_result.scalars().all()

    logger.info(
        "extension.bootstrap.loaded",
        extension_id=extension_id,
        extension_version=extension_version,
        tenant_id=str(tenant_id),
        user_id=str(user.id),
    )
    return BrowserExtensionBootstrapResponse(
        user=BrowserExtensionUserSummary(
            id=user.id,
            email=user.email,
            name=user.name,
            is_superuser=user.is_superuser,
        ),
        linkedin=BrowserExtensionLinkedInStatus(
            connected=linkedin_account is not None,
            display_name=linkedin_account.display_name if linkedin_account else None,
        ),
        features=_extension_feature_flags(),
        recent_engagement_sessions=[
            BrowserExtensionRecentEngagementSession(
                id=session.id,
                status=session.status,
                scan_source=session.scan_source,
                created_at=session.created_at,
            )
            for session in sessions
        ],
    )


@router.post(
    "/engagement/sessions",
    response_model=BrowserExtensionRecentEngagementSession,
    status_code=status.HTTP_201_CREATED,
)
async def create_extension_engagement_session(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user_payload: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> BrowserExtensionRecentEngagementSession:
    if not settings.EXTENSION_LINKEDIN_CAPTURE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Captura via extensao desabilitada neste ambiente.",
        )

    extension_id, extension_version = _get_extension_headers(request)
    now = datetime.now(UTC)
    session = ContentEngagementSession(
        tenant_id=tenant_id,
        status="completed",
        scan_source="manual",
        completed_at=now,
    )
    db.add(session)
    await db.flush()

    db.add(
        ContentEngagementEvent(
            tenant_id=tenant_id,
            session_id=session.id,
            event_type="extension_manual_session_created",
            payload={
                "extension_id": extension_id,
                "extension_version": extension_version,
                "created_by_user_id": str(user_payload.user_id),
            },
        )
    )
    await db.commit()
    await db.refresh(session)

    logger.info(
        "extension.engagement_session.created",
        extension_id=extension_id,
        extension_version=extension_version,
        tenant_id=str(tenant_id),
        user_id=str(user_payload.user_id),
        session_id=str(session.id),
    )
    return BrowserExtensionRecentEngagementSession(
        id=session.id,
        status=session.status,
        scan_source=session.scan_source,
        created_at=session.created_at,
    )


@router.post(
    "/capture/statuses",
    response_model=BrowserExtensionImportStatusResponse,
)
async def get_extension_capture_statuses(
    body: BrowserExtensionImportStatusRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user_payload: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> BrowserExtensionImportStatusResponse:
    extension_id, extension_version = _get_extension_headers(request)

    candidate_identity_map: dict[str, tuple[str | None, str | None]] = {}
    canonical_urls: set[str] = set()
    dedup_keys: set[str] = set()

    for candidate in body.candidates:
        canonical_post_url, dedup_key = build_post_identity(
            post_url=candidate.canonical_post_url or candidate.post_url,
            post_text=candidate.post_text,
            author_name=candidate.author_name,
        )
        candidate_identity_map[candidate.candidate_key] = (canonical_post_url, dedup_key)
        if canonical_post_url:
            canonical_urls.add(canonical_post_url)
        if dedup_key:
            dedup_keys.add(dedup_key)

    capture_by_canonical_url: dict[str, ContentExtensionCapture] = {}
    capture_by_dedup_key: dict[str, ContentExtensionCapture] = {}
    if canonical_urls or dedup_keys:
        capture_stmt = select(ContentExtensionCapture).where(
            ContentExtensionCapture.tenant_id == tenant_id,
            ContentExtensionCapture.source_platform == "linkedin",
        )
        if canonical_urls and dedup_keys:
            capture_stmt = capture_stmt.where(
                or_(
                    ContentExtensionCapture.canonical_post_url.in_(canonical_urls),
                    ContentExtensionCapture.dedup_key.in_(dedup_keys),
                )
            )
        elif canonical_urls:
            capture_stmt = capture_stmt.where(
                ContentExtensionCapture.canonical_post_url.in_(canonical_urls)
            )
        else:
            capture_stmt = capture_stmt.where(ContentExtensionCapture.dedup_key.in_(dedup_keys))

        capture_result = await db.execute(
            capture_stmt.order_by(ContentExtensionCapture.created_at.desc())
        )
        for capture in capture_result.scalars().all():
            if (
                capture.canonical_post_url
                and capture.canonical_post_url not in capture_by_canonical_url
            ):
                capture_by_canonical_url[capture.canonical_post_url] = capture
            if capture.dedup_key and capture.dedup_key not in capture_by_dedup_key:
                capture_by_dedup_key[capture.dedup_key] = capture

    matches: list[BrowserExtensionImportStatusMatch] = []
    for candidate in body.candidates:
        canonical_post_url, dedup_key = candidate_identity_map[candidate.candidate_key]
        matched_capture: ContentExtensionCapture | None = None
        if canonical_post_url:
            matched_capture = capture_by_canonical_url.get(canonical_post_url)
        if matched_capture is None and dedup_key:
            matched_capture = capture_by_dedup_key.get(dedup_key)

        matches.append(
            BrowserExtensionImportStatusMatch(
                candidate_key=candidate.candidate_key,
                imported=matched_capture is not None,
                destination_type=(
                    "reference"
                    if matched_capture and matched_capture.destination_type == "reference"
                    else "engagement"
                    if matched_capture and matched_capture.destination_type == "engagement"
                    else None
                ),
                linked_object_type=matched_capture.linked_object_type if matched_capture else None,
                linked_object_id=matched_capture.linked_object_id if matched_capture else None,
            )
        )

    logger.info(
        "extension.capture_statuses.resolved",
        extension_id=extension_id,
        extension_version=extension_version,
        tenant_id=str(tenant_id),
        user_id=str(user_payload.user_id),
        candidates_count=len(body.candidates),
        imported_count=sum(1 for match in matches if match.imported),
    )
    return BrowserExtensionImportStatusResponse(matches=matches)


@router.post(
    "/capture/linkedin-post",
    response_model=BrowserExtensionCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def capture_linkedin_post(
    body: BrowserExtensionCaptureRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user_payload: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> BrowserExtensionCaptureResponse:
    if not settings.EXTENSION_LINKEDIN_CAPTURE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Captura via extensao desabilitada neste ambiente.",
        )

    extension_id, extension_version_header = _get_extension_headers(request)
    await _check_extension_capture_rate_limit(tenant_id=tenant_id, user_id=user_payload.user_id)

    canonical_post_url, dedup_key = build_post_identity(
        post_url=body.post.canonical_post_url or body.post.post_url,
        post_text=body.post.post_text,
        author_name=body.post.author_name,
    )
    client_context = body.client_context.model_dump(mode="json", exclude_none=True)
    if extension_version_header and "extension_version" not in client_context:
        client_context["extension_version"] = extension_version_header
    client_context["extension_id"] = extension_id

    result: Literal["created", "merged"]
    linked_object_type: str
    linked_object_id: uuid.UUID

    if body.destination.type == "reference":
        matched_reference = await _load_reference_match(
            db,
            tenant_id=tenant_id,
            dedup_key=dedup_key,
        )

        if matched_reference is None:
            matched_reference = ContentReference(
                tenant_id=tenant_id,
                author_name=body.post.author_name,
                author_title=body.post.author_title,
                author_company=body.post.author_company,
                body=body.post.post_text,
                engagement_score=_compute_engagement_score(
                    likes=body.post.likes,
                    comments=body.post.comments,
                    shares=body.post.shares,
                )
                or None,
                source_url=canonical_post_url or body.post.post_url,
            )
            db.add(matched_reference)
            await db.flush()
            result = cast(Literal["created", "merged"], "created")
        else:
            _merge_reference_payload(matched_reference, body)
            db.add(matched_reference)
            result = cast(Literal["created", "merged"], "merged")

        linked_object_type = "reference"
        linked_object_id = matched_reference.id
        response = BrowserExtensionCaptureResponse(
            destination="reference",
            result=result,
            dedup_key=dedup_key,
            reference_id=matched_reference.id,
        )
    else:
        if body.destination.session_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="session_id e obrigatorio quando o destino for engagement.",
            )

        await _load_session_or_404(
            db,
            session_id=body.destination.session_id,
            tenant_id=tenant_id,
        )
        engagement_post_type = "icp" if body.post.post_type != "icp" else body.post.post_type
        manual_post_payload = AddManualPostRequest(
            source="manual",
            post_url=body.post.post_url,
            post_text=body.post.post_text,
            author_name=body.post.author_name,
            author_title=body.post.author_title,
            author_company=body.post.author_company,
            author_profile_url=body.post.author_profile_url,
            post_type=engagement_post_type,
            likes=body.post.likes,
            comments=body.post.comments,
            shares=body.post.shares,
        )
        engagement_post, created = await _upsert_external_post(
            db,
            session_id=body.destination.session_id,
            tenant_id=tenant_id,
            body=manual_post_payload,
        )
        linked_object_type = "engagement_post"
        linked_object_id = engagement_post.id
        result = "created" if created else "merged"
        response = BrowserExtensionCaptureResponse(
            destination="engagement",
            result=result,
            dedup_key=engagement_post.dedup_key or dedup_key,
            session_id=body.destination.session_id,
            engagement_post_id=engagement_post.id,
        )

    await _record_capture_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_payload.user_id,
        destination_type=body.destination.type,
        result=result,
        source_url=body.post.post_url,
        canonical_post_url=canonical_post_url,
        dedup_key=response.dedup_key,
        linked_object_type=linked_object_type,
        linked_object_id=linked_object_id,
        client_context=client_context,
        captured_payload=body.post.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()

    logger.info(
        "extension.capture.imported",
        extension_id=extension_id,
        tenant_id=str(tenant_id),
        user_id=str(user_payload.user_id),
        destination=body.destination.type,
        result=result,
        linked_object_type=linked_object_type,
        linked_object_id=str(linked_object_id),
    )
    return response
