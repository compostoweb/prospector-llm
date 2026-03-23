"""
services/email_finder.py

Orquestra a cascata de finders para localizar o e-mail corporativo de um lead.

Ordem de tentativas:
  1. Unipile  — e-mail já armazenado no lead (sem custo de API)
  2. Prospeo  — maior precisão para Brasil/PT
  3. Hunter   — boa cobertura global
  4. Apollo   — fallback via LinkedIn URL

Após encontrar o e-mail:
  - Classifica como corporativo ou pessoal (heurística por domínio)
  - Valida via ZeroBounce (fail open em caso de timeout)

Retorna EmailFindResult ou None se todos os finders falharem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from integrations.email_finders.apollo import ApolloClient
from integrations.email_finders.hunter import HunterClient
from integrations.email_finders.prospeo import ProspeoClient
from integrations.zerobounce import ZeroBounceClient
from models.enums import EmailType

logger = structlog.get_logger()

# Domínios de e-mail pessoal mais comuns no Brasil e no mundo
_PERSONAL_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "yahoo.com.br", "hotmail.com", "outlook.com",
    "live.com", "msn.com", "bol.com.br", "uol.com.br", "terra.com.br",
    "ig.com.br", "r7.com", "protonmail.com", "icloud.com", "me.com",
    "mac.com", "aol.com", "gmx.com", "yandex.com",
})

_NAME_RE = re.compile(r"[^\w\s'-]")


@dataclass
class EmailFindResult:
    email: str
    source: str          # "prospeo" | "hunter" | "apollo"
    email_type: EmailType
    confidence: float    # 0.0 – 1.0
    verified: bool       # resultado do ZeroBounce


class EmailFinderService:
    """
    Cascata de finders de e-mail com validação ZeroBounce integrada.
    """

    def __init__(self) -> None:
        self._prospeo = ProspeoClient()
        self._hunter = HunterClient()
        self._apollo = ApolloClient()
        self._zerobounce = ZeroBounceClient()

    async def find(
        self,
        first_name: str,
        last_name: str,
        domain: str | None,
        linkedin_url: str | None = None,
        existing_email: str | None = None,
    ) -> EmailFindResult | None:
        """
        Cascata de busca de e-mail.

        Parâmetros:
          first_name / last_name: nome do lead
          domain: domínio corporativo (ex: "empresa.com.br") — None se desconhecido
          linkedin_url: URL do perfil LinkedIn (para Apollo)
          existing_email: e-mail já armazenado no lead (curto-circuita a cascata)
        """
        # ── 1. Já temos um e-mail? Apenas valida e classifica ──────────
        if existing_email:
            verified = await self._zerobounce.validate(existing_email)
            email_type = _classify_email(existing_email)
            return EmailFindResult(
                email=existing_email,
                source="existing",
                email_type=email_type,
                confidence=1.0,
                verified=verified,
            )

        first = _clean_name(first_name)
        last = _clean_name(last_name)

        # ── 2. Prospeo (precisa de domínio) ───────────────────────────
        if domain:
            result = await self._prospeo.find_email(first, last, domain)
            if result:
                email, confidence = result
                return await self._finalize(email, "prospeo", confidence)

        # ── 3. Hunter (precisa de domínio) ────────────────────────────
        if domain:
            result = await self._hunter.find_email(first, last, domain)
            if result:
                email, confidence = result
                return await self._finalize(email, "hunter", confidence)

        # ── 4. Apollo (via LinkedIn URL) ──────────────────────────────
        if linkedin_url:
            result = await self._apollo.find_email(linkedin_url)
            if result:
                email, confidence = result
                return await self._finalize(email, "apollo", confidence)

        logger.info(
            "email_finder.not_found",
            first=first,
            last=last,
            domain=domain,
            linkedin_url=linkedin_url,
        )
        return None

    # ── Helpers ───────────────────────────────────────────────────────

    async def _finalize(
        self,
        email: str,
        source: str,
        confidence: float,
    ) -> EmailFindResult:
        verified = await self._zerobounce.validate(email)
        email_type = _classify_email(email)
        logger.info(
            "email_finder.found",
            email=email,
            source=source,
            email_type=email_type.value,
            verified=verified,
            confidence=confidence,
        )
        return EmailFindResult(
            email=email,
            source=source,
            email_type=email_type,
            confidence=confidence,
            verified=verified,
        )

    async def aclose(self) -> None:
        await self._prospeo.aclose()
        await self._hunter.aclose()
        await self._apollo.aclose()
        await self._zerobounce.aclose()


# ── Utilitários ───────────────────────────────────────────────────────

def _classify_email(email: str) -> EmailType:
    """Classifica o e-mail como corporativo ou pessoal pelo domínio."""
    try:
        domain = email.split("@", 1)[1].lower()
        if domain in _PERSONAL_DOMAINS:
            return EmailType.PERSONAL
        return EmailType.CORPORATE
    except IndexError:
        return EmailType.UNKNOWN


def _clean_name(name: str) -> str:
    """Remove caracteres especiais do nome para melhorar resultados de busca."""
    return _NAME_RE.sub("", name).strip()
