from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_session_no_auth
from api.main import app
from api.routes.content import calculator as calculator_routes
from models.content_calculator_result import ContentCalculatorResult

pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(self, *, scalar_one_or_none_value: object | None = None) -> None:
        self._scalar_one_or_none_value = scalar_one_or_none_value

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_one_or_none_value


class FakeAsyncSession:
    def __init__(self, tenant_id: uuid.UUID) -> None:
        self.tenant_id = tenant_id
        self.result: ContentCalculatorResult | None = None
        self.commits = 0
        self.refreshes = 0

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> FakeResult:
        compiled = str(statement)
        if "FROM tenants" in compiled:
            return FakeResult(scalar_one_or_none_value=self.tenant_id)
        if "FROM content_calculator_results" in compiled:
            return FakeResult(scalar_one_or_none_value=self.result)
        if "FROM content_lead_magnets" in compiled:
            return FakeResult(scalar_one_or_none_value=None)
        raise AssertionError(f"Unexpected statement in fake session: {compiled}")

    def add(self, instance: object) -> None:
        if isinstance(instance, ContentCalculatorResult):
            if getattr(instance, "id", None) is None:
                instance.id = uuid.uuid4()
            self.result = instance

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        self.refreshes += 1
        if isinstance(instance, ContentCalculatorResult) and getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()


@pytest.fixture
async def raw_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


async def test_calculator_calculate_and_convert_creates_prospect_and_notifies(
    raw_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeAsyncSession(tenant_id=uuid.uuid4())
    lead_id = uuid.uuid4()
    queue_calls: list[str] = []
    convert_calls: list[dict[str, object | None]] = []
    diagnosis_email_calls: list[dict[str, str | None]] = []
    notification_calls: list[dict[str, str | None]] = []

    async def _override_session() -> AsyncGenerator[FakeAsyncSession, None]:
        yield fake_db

    async def fake_queue_sendpulse_sync(_lm_lead: object) -> None:
        queue_calls.append("queued")

    async def fake_convert_inbound_contact_to_prospect(
        db: FakeAsyncSession,
        *,
        tenant_id: uuid.UUID,
        name: str,
        email: str,
        company: str | None,
        role: str | None,
        phone: str | None,
        note: str,
        extra_tags: list[str] | None = None,
    ) -> SimpleNamespace:
        convert_calls.append(
            {
                "db_is_fake": db is fake_db,
                "tenant_id": str(tenant_id),
                "name": name,
                "email": email,
                "company": company,
                "role": role,
                "phone": phone,
                "note": note,
                "extra_tags": ",".join(extra_tags or []),
            }
        )
        return SimpleNamespace(id=lead_id)

    async def fake_send_calculator_submission_notification(
        *,
        result: ContentCalculatorResult,
        lead_magnet_title: str | None = None,
        lm_lead_id: uuid.UUID | None = None,
        sendpulse_sync_status: str | None = None,
        diagnosis_email_sent: bool | None = None,
    ) -> bool:
        notification_calls.append(
            {
                "result_id": str(result.id),
                "lead_id": str(result.lead_id) if result.lead_id else None,
                "lead_magnet_title": lead_magnet_title,
                "lm_lead_id": str(lm_lead_id) if lm_lead_id else None,
                "sendpulse_sync_status": sendpulse_sync_status,
                "diagnosis_email_sent": str(diagnosis_email_sent),
            }
        )
        return True

    async def fake_send_calculator_diagnosis_email(
        *,
        result: ContentCalculatorResult,
        lead_magnet_title: str | None = None,
    ) -> bool:
        diagnosis_email_calls.append(
            {
                "result_id": str(result.id),
                "email": result.email,
                "lead_magnet_title": lead_magnet_title,
            }
        )
        return True

    monkeypatch.setattr(
        calculator_routes,
        "convert_inbound_contact_to_prospect",
        fake_convert_inbound_contact_to_prospect,
    )
    monkeypatch.setattr(calculator_routes, "queue_sendpulse_sync", fake_queue_sendpulse_sync)
    monkeypatch.setattr(
        calculator_routes,
        "send_calculator_diagnosis_email",
        fake_send_calculator_diagnosis_email,
    )
    monkeypatch.setattr(
        calculator_routes,
        "send_calculator_submission_notification",
        fake_send_calculator_submission_notification,
    )
    app.dependency_overrides[get_session_no_auth] = _override_session

    try:
        calculate_response = await raw_client.post(
            "/api/content/calculator/calculate",
            json={
                "pessoas": 4,
                "horas_semana": 18,
                "custo_hora": 140,
                "cargo": "gerente",
                "retrabalho_pct": 20,
                "tipo_processo": "financeiro",
                "company_segment": "industria",
                "company_size": "media",
                "process_area_span": "2-3",
                "session_id": "sessao-calculadora-1",
            },
        )

        assert calculate_response.status_code == 201
        calculate_body = calculate_response.json()
        result_id = uuid.UUID(calculate_body["result_id"])
        assert calculate_body["custo_anual"] > 0
        assert calculate_body["roi_estimado"] > 0

        convert_response = await raw_client.post(
            "/api/content/calculator/convert",
            json={
                "result_id": str(result_id),
                "name": "Ana Oliveira",
                "email": "ANA@EMPRESA.COM.BR",
                "company": "Empresa XPTO",
                "role": "Diretora Financeira",
                "phone": "11999990000",
                "create_prospect": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_session_no_auth, None)

    assert convert_response.status_code == 200
    convert_body = convert_response.json()
    assert convert_body["result_id"] == str(result_id)
    assert convert_body["lead_id"] == str(lead_id)
    assert convert_body["lm_lead_id"] is None
    assert convert_body["sendpulse_sync_status"] is None
    assert convert_body["diagnosis_email_sent"] is True
    assert convert_body["internal_notification_sent"] is True

    assert fake_db.result is not None
    assert fake_db.result.id == result_id
    assert fake_db.result.converted_to_lead is True
    assert fake_db.result.lead_id == lead_id
    assert fake_db.result.name == "Ana Oliveira"
    assert fake_db.result.email == "ana@empresa.com.br"
    assert fake_db.result.company == "Empresa XPTO"
    assert fake_db.result.role == "Diretora Financeira"
    assert fake_db.result.phone == "11999990000"
    assert fake_db.result.company_segment == "industria"
    assert fake_db.result.company_size == "media"
    assert fake_db.result.process_area_span == "2-3"
    assert fake_db.commits == 2
    assert fake_db.refreshes == 2

    assert len(convert_calls) == 1
    convert_call = convert_calls[0]
    assert convert_call["db_is_fake"] is True
    assert convert_call["tenant_id"] == str(fake_db.tenant_id)
    assert convert_call["name"] == "Ana Oliveira"
    assert convert_call["email"] == "ana@empresa.com.br"
    assert convert_call["company"] == "Empresa XPTO"
    assert convert_call["role"] == "Diretora Financeira"
    assert convert_call["phone"] == "11999990000"
    assert convert_call["extra_tags"] == "calculator_conversion"
    assert isinstance(convert_call["note"], str)
    assert "Origem inbound: calculadora de ROI" in str(convert_call["note"])
    assert "ROI estimado" in str(convert_call["note"])
    assert "Segmento: industria" in str(convert_call["note"])
    assert "Porte: media" in str(convert_call["note"])
    assert "Áreas: 2-3" in str(convert_call["note"])

    assert queue_calls == []
    assert diagnosis_email_calls == [
        {
            "result_id": str(result_id),
            "email": "ana@empresa.com.br",
            "lead_magnet_title": None,
        }
    ]
    assert notification_calls == [
        {
            "result_id": str(result_id),
            "lead_id": str(lead_id),
            "lead_magnet_title": None,
            "lm_lead_id": None,
            "sendpulse_sync_status": None,
            "diagnosis_email_sent": "True",
        }
    ]
