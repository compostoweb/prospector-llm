import pytest
from fastapi import HTTPException

from api.routes.content.landing_pages import _validate_capture_fields_for_type
from schemas.content_inbound import LandingPagePublicCaptureRequest


def _capture(**overrides: object) -> LandingPagePublicCaptureRequest:
    payload = {
        "name": "João Silva",
        "email": "joao@empresa.com",
        "company": None,
        "role": None,
        "phone": None,
    }
    payload.update(overrides)
    return LandingPagePublicCaptureRequest.model_validate(payload)


def test_link_capture_accepts_name_and_email_only() -> None:
    _validate_capture_fields_for_type(lead_magnet_type="link", form_fields=None, body=_capture())


def test_pdf_capture_requires_company() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_capture_fields_for_type(lead_magnet_type="pdf", form_fields=None, body=_capture())

    assert exc_info.value.status_code == 422
    assert "company" in str(exc_info.value.detail)


def test_email_sequence_capture_requires_company_and_role() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_capture_fields_for_type(
            lead_magnet_type="email_sequence",
            form_fields=None,
            body=_capture(),
        )

    assert exc_info.value.status_code == 422
    assert "company" in str(exc_info.value.detail)
    assert "role" in str(exc_info.value.detail)


def test_email_sequence_capture_accepts_required_fields() -> None:
    _validate_capture_fields_for_type(
        lead_magnet_type="email_sequence",
        form_fields=None,
        body=_capture(company="Empresa Demo", role="Diretor"),
    )


def test_custom_lp_form_fields_override_type_defaults() -> None:
    _validate_capture_fields_for_type(
        lead_magnet_type="email_sequence",
        form_fields=[
            {"key": "name", "required": True},
            {"key": "email", "required": True},
        ],
        body=_capture(),
    )


def test_custom_lp_required_phone_is_validated() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_capture_fields_for_type(
            lead_magnet_type="link",
            form_fields=[
                {"key": "name", "required": True},
                {"key": "email", "required": True},
                {"key": "phone", "required": True},
            ],
            body=_capture(),
        )

    assert exc_info.value.status_code == 422
    assert "phone" in str(exc_info.value.detail)