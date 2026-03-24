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


def _base_url(domain: str | None = None) -> str:
    d = domain or settings.PIPEDRIVE_DOMAIN or "app"
    return f"https://{d}.pipedrive.com/api/v2"


def _base_url_v1(domain: str | None = None) -> str:
    d = domain or settings.PIPEDRIVE_DOMAIN or "app"
    return f"https://{d}.pipedrive.com/v1"


class PipedriveClient:
    def __init__(self, token: str | None = None, domain: str | None = None) -> None:
        self._client = httpx.AsyncClient(
            timeout=_TIMEOUT,
        )
        self._token = token or settings.PIPEDRIVE_API_TOKEN or ""
        self._domain = domain

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
                f"{_base_url(self._domain)}/persons/search",
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
                f"{_base_url(self._domain)}/persons",
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
                f"{_base_url(self._domain)}/deals",
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
                f"{_base_url(self._domain)}/notes",
                params=self._params(),
                json={"content": content, "deal_id": deal_id},
            )
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.add_note_error", deal_id=deal_id, error=str(exc))
            return False

    # ── Metadata (pipelines, stages, users) ──────────────────────────

    async def get_pipelines(self) -> list[dict]:
        """Lista todos os pipelines. Retorna lista de {id, name}."""
        try:
            resp = await self._client.get(
                f"{_base_url_v1(self._domain)}/pipelines",
                params=self._params(),
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            return [{"id": p["id"], "name": p["name"]} for p in data]
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.get_pipelines_error", error=str(exc))
            return []

    async def get_stages(self, pipeline_id: int | None = None) -> list[dict]:
        """Lista stages. Se pipeline_id informado, filtra por pipeline."""
        try:
            extra: dict = {}
            if pipeline_id is not None:
                extra["pipeline_id"] = pipeline_id
            resp = await self._client.get(
                f"{_base_url_v1(self._domain)}/stages",
                params=self._params(extra),
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            return [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "pipeline_id": s["pipeline_id"],
                    "order_nr": s.get("order_nr", 0),
                }
                for s in data
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.get_stages_error", error=str(exc))
            return []

    async def get_users(self) -> list[dict]:
        """Lista usuários ativos do Pipedrive. Retorna lista de {id, name, email}."""
        try:
            resp = await self._client.get(
                f"{_base_url_v1(self._domain)}/users",
                params=self._params(),
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            return [
                {"id": u["id"], "name": u["name"], "email": u["email"]}
                for u in data
                if u.get("active_flag", False)
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("pipedrive.get_users_error", error=str(exc))
            return []

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PipedriveClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton
pipedrive_client = PipedriveClient()
