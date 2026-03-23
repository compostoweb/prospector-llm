"""
integrations/pipedrive_client.py

Cliente HTTP assíncrono para Pipedrive CRM — cria e atualiza deals.

Base URL: https://{domain}.pipedrive.com/api/v2
Auth:     api_token query param

Responsabilidades:
  - Criar deal quando lead responde com INTEREST ou OBJECTION
  - Buscar person existente (deduplicação por e-mail ou nome)
  - Criar person se não existir
  - Associar deal ao owner configurado nas settings
  - Adicionar nota com o resumo da conversa (summary da intenção)

Fluxo típico de uso (via dispatch_worker no reply handler):
  person_id = await client.find_or_create_person(name, email)
  deal_id   = await client.create_deal(person_id, title, stage_id, value)
  if notes:  await client.add_note(deal_id, note_text)
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_TIMEOUT = 20.0


def _base_url() -> str:
    domain = settings.PIPEDRIVE_DOMAIN or "app"
    return f"https://{domain}.pipedrive.com/api/v2"


class PipedriveClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=_TIMEOUT,
        )
        self._token = settings.PIPEDRIVE_API_TOKEN or ""

    def _params(self, extra: dict | None = None) -> dict:
        """Retorna params base com api_token + extras opcionais."""
        p: dict = {"api_token": self._token}
        if extra:
            p.update(extra)
        return p

    # ── Persons ───────────────────────────────────────────────────────

    async def find_person_by_email(self, email: str) -> int | None:
        """Busca person pelo e-mail. Retorna person_id ou None."""
        try:
            resp = await self._client.get(
                f"{_base_url()}/persons/search",
                params=self._params({"term": email, "fields": "email", "limit": 1}),
            )
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("items", [])
            if items:
                return items[0]["item"]["id"]
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.find_person_error", email=email, error=str(exc))
            return None

    async def create_person(
        self,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        linkedin_url: str | None = None,
    ) -> int | None:
        """Cria person no Pipedrive. Retorna person_id ou None em caso de erro."""
        body: dict = {"name": name}
        if email:
            body["email"] = [{"value": email, "primary": True}]
        if phone:
            body["phone"] = [{"value": phone, "primary": True}]
        if linkedin_url:
            body["linkedin"] = linkedin_url

        try:
            resp = await self._client.post(
                f"{_base_url()}/persons",
                params=self._params(),
                json=body,
            )
            resp.raise_for_status()
            person_id: int = resp.json()["data"]["id"]
            logger.info("pipedrive.person_created", name=name, person_id=person_id)
            return person_id
        except Exception as exc:  # noqa: BLE001
            logger.error("pipedrive.create_person_error", name=name, error=str(exc))
            return None

    async def find_or_create_person(
        self,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        linkedin_url: str | None = None,
    ) -> int | None:
        """Localiza person pelo e-mail; cria se não existir."""
        if email:
            person_id = await self.find_person_by_email(email)
            if person_id:
                return person_id
        return await self.create_person(name, email, phone, linkedin_url)

    # ── Deals ─────────────────────────────────────────────────────────

    async def create_deal(
        self,
        title: str,
        person_id: int | None = None,
        stage_id: int | None = None,
        owner_id: int | None = None,
        value: float = 0.0,
    ) -> int | None:
        """
        Cria um deal no Pipedrive.

        stage_id: usa settings.PIPEDRIVE_STAGE_INTEREST ou STAGE_OBJECTION
        Retorna deal_id ou None em caso de erro.
        """
        body: dict = {
            "title": title,
            "value": value,
            "currency": "BRL",
        }
        if person_id:
            body["person_id"] = person_id
        if stage_id:
            body["stage_id"] = stage_id
        if owner_id or settings.PIPEDRIVE_OWNER_ID:
            body["user_id"] = owner_id or settings.PIPEDRIVE_OWNER_ID

        try:
            resp = await self._client.post(
                f"{_base_url()}/deals",
                params=self._params(),
                json=body,
            )
            resp.raise_for_status()
            deal_id: int = resp.json()["data"]["id"]
            logger.info(
                "pipedrive.deal_created",
                title=title,
                deal_id=deal_id,
                stage_id=stage_id,
            )
            return deal_id
        except Exception as exc:  # noqa: BLE001
            logger.error("pipedrive.create_deal_error", title=title, error=str(exc))
            return None

    # ── Notes ─────────────────────────────────────────────────────────

    async def add_note(self, deal_id: int, content: str) -> bool:
        """Adiciona nota de texto a um deal. Retorna True se bem-sucedido."""
        try:
            resp = await self._client.post(
                f"{_base_url()}/notes",
                params=self._params(),
                json={"content": content, "deal_id": deal_id},
            )
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.add_note_error", deal_id=deal_id, error=str(exc))
            return False

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PipedriveClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton
pipedrive_client = PipedriveClient()
