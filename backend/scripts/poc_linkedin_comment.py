"""
scripts/poc_linkedin_comment.py

POC: validar empiricamente como publicar e fixar (pin) um comentário no
PRÓPRIO post UGC do tenant. Testa duas APIs em sequência:

  1. LinkedIn API oficial (v2):
     - POST /v2/socialActions               → cria comentário
     - POST /v2/socialActions/.../action=pin → tenta fixar (best-effort)
  2. Unipile:
     - POST /api/v1/linkedin/posts/{post_id}/comments → cria comentário

Uso:
    cd backend
    # Variáveis necessárias:
    #   LINKEDIN_ACCESS_TOKEN   (do tenant; scope w_member_social)
    #   LINKEDIN_PERSON_URN     (urn:li:person:XXXX)
    #   LINKEDIN_POST_URN       (urn:li:ugcPost:XXXX já publicado)
    #   COMMENT_TEXT            (texto do comentário)
    #   UNIPILE_API_KEY         (opcional; pula Unipile se ausente)
    #   UNIPILE_BASE_URL        (opcional; default da env)
    #   UNIPILE_ACCOUNT_ID      (opcional; usado p/ Unipile)
    #   UNIPILE_POST_LOCAL_ID   (opcional; ID interno Unipile do post — não URN)

    python scripts/poc_linkedin_comment.py

Saída esperada: JSON com resultado de cada tentativa (status_code + body).

ATENÇÃO: este script PUBLICA um comentário real. Use em conta de testes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import httpx


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"[ERRO] Variável de ambiente {name} é obrigatória.", file=sys.stderr)
        sys.exit(1)
    return value


def _optional(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


async def try_linkedin_official_create_comment(
    *,
    access_token: str,
    person_urn: str,
    post_urn: str,
    comment_text: str,
) -> dict[str, Any]:
    """Tenta POST /v2/socialActions para criar comentário no próprio post."""
    payload = {
        "actor": person_urn,
        "object": post_urn,
        "message": {"text": comment_text},
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.linkedin.com/v2/socialActions",
            json=payload,
            headers=headers,
        )

    body: Any
    try:
        body = response.json()
    except ValueError:
        body = response.text

    return {
        "endpoint": "POST /v2/socialActions",
        "status_code": response.status_code,
        "response_body": body,
        "comment_urn": (
            response.headers.get("x-restli-id")
            or response.headers.get("X-RestLi-Id")
            or (body.get("$URN") if isinstance(body, dict) else None)
        ),
    }


async def try_linkedin_official_pin_comment(
    *,
    access_token: str,
    post_urn: str,
    comment_urn: str,
) -> dict[str, Any]:
    """
    Tenta fixar (pin) o comentário criado.

    A LinkedIn não documenta publicamente um endpoint pin para comentários
    em posts UGC pessoais. Este teste registra o resultado para decidirmos
    se a feature será marcada como 'not_supported'.

    Tentativas (em ordem):
      1. POST /v2/socialActions/{post_urn}/comments/{comment_urn}?action=pin
      2. POST /v2/socialActions/{post_urn}?action=pinComment com {comment}
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    encoded_post = post_urn.replace(":", "%3A")
    encoded_comment = comment_urn.replace(":", "%3A") if comment_urn else ""

    attempts: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        if encoded_comment:
            url = (
                f"https://api.linkedin.com/v2/socialActions/{encoded_post}"
                f"/comments/{encoded_comment}?action=pin"
            )
            r = await client.post(url, json={}, headers=headers)
            attempts.append(
                {
                    "endpoint": url,
                    "status_code": r.status_code,
                    "response_body": _safe_body(r),
                }
            )

        url2 = (
            f"https://api.linkedin.com/v2/socialActions/{encoded_post}?action=pinComment"
        )
        r = await client.post(
            url2,
            json={"comment": comment_urn},
            headers=headers,
        )
        attempts.append(
            {
                "endpoint": url2,
                "status_code": r.status_code,
                "response_body": _safe_body(r),
            }
        )

    return {"pin_attempts": attempts}


async def try_unipile_create_comment(
    *,
    api_key: str,
    base_url: str,
    account_id: str,
    post_local_id: str,
    comment_text: str,
) -> dict[str, Any]:
    """Tenta POST /api/v1/linkedin/posts/{post_id}/comments via Unipile."""
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"account_id": account_id, "text": comment_text}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/api/v1/linkedin/posts/{post_local_id}/comments",
            json=payload,
            headers=headers,
        )

    return {
        "endpoint": f"POST /api/v1/linkedin/posts/{post_local_id}/comments",
        "status_code": response.status_code,
        "response_body": _safe_body(response),
    }


def _safe_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text[:500]


async def main() -> None:
    access_token = _require("LINKEDIN_ACCESS_TOKEN")
    person_urn = _require("LINKEDIN_PERSON_URN")
    post_urn = _require("LINKEDIN_POST_URN")
    comment_text = _require("COMMENT_TEXT")

    unipile_api_key = _optional("UNIPILE_API_KEY")
    unipile_base_url = _optional("UNIPILE_BASE_URL") or "https://api2.unipile.com:13246"
    unipile_account_id = _optional("UNIPILE_ACCOUNT_ID")
    unipile_post_local_id = _optional("UNIPILE_POST_LOCAL_ID")

    report: dict[str, Any] = {"official": {}, "unipile": {}}

    # ── 1. Oficial: criar comentário ──────────────────────────────────
    print("[1/3] Tentando criar comentário via API oficial LinkedIn...", file=sys.stderr)
    official = await try_linkedin_official_create_comment(
        access_token=access_token,
        person_urn=person_urn,
        post_urn=post_urn,
        comment_text=comment_text,
    )
    report["official"]["create_comment"] = official

    # ── 2. Oficial: tentar pin ────────────────────────────────────────
    comment_urn = official.get("comment_urn") or ""
    if official.get("status_code") in (200, 201) and comment_urn:
        print("[2/3] Tentando fixar (pin) comentário via API oficial...", file=sys.stderr)
        pin = await try_linkedin_official_pin_comment(
            access_token=access_token,
            post_urn=post_urn,
            comment_urn=comment_urn,
        )
        report["official"]["pin_comment"] = pin
    else:
        report["official"]["pin_comment"] = {
            "skipped": True,
            "reason": "Comentário oficial não foi criado.",
        }

    # ── 3. Unipile: criar comentário ──────────────────────────────────
    if unipile_api_key and unipile_account_id and unipile_post_local_id:
        print("[3/3] Tentando criar comentário via Unipile...", file=sys.stderr)
        unipile = await try_unipile_create_comment(
            api_key=unipile_api_key,
            base_url=unipile_base_url,
            account_id=unipile_account_id,
            post_local_id=unipile_post_local_id,
            comment_text=comment_text + " (via unipile)",
        )
        report["unipile"]["create_comment"] = unipile
    else:
        report["unipile"] = {
            "skipped": True,
            "reason": "UNIPILE_API_KEY / UNIPILE_ACCOUNT_ID / UNIPILE_POST_LOCAL_ID ausentes.",
        }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
