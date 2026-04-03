"""
api/routes/content/__init__.py

Router pai do modulo Content Hub.
Agrega todos os sub-routers com prefix /content.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.content import posts, themes, settings, references, linkedin_auth, generate

router = APIRouter(prefix="/content", tags=["Content Hub"])

router.include_router(posts.router)
router.include_router(themes.router)
router.include_router(settings.router)
router.include_router(references.router)
router.include_router(linkedin_auth.router)
router.include_router(generate.router)
