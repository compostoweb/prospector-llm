"""
api/routes/content/__init__.py

Router pai do modulo Content Hub.
Agrega todos os sub-routers com prefix /content.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.content import (
	calculator,
	generate,
	landing_pages,
	lead_magnets,
	linkedin_auth,
	posts,
	references,
	settings,
	themes,
)

router = APIRouter(prefix="/content", tags=["Content Hub"])

router.include_router(posts.router)
router.include_router(themes.router)
router.include_router(settings.router)
router.include_router(references.router)
router.include_router(linkedin_auth.router)
router.include_router(generate.router)
router.include_router(lead_magnets.router)
router.include_router(landing_pages.router)
router.include_router(calculator.router)
