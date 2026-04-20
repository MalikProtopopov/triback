"""Public (guest) endpoints — no authentication required.

Assembles sub-routers from domain-specific modules.
"""

from fastapi import APIRouter

from app.api.v1.public.articles import router as articles_router
from app.api.v1.public.certificates import router as certificates_router
from app.api.v1.public.cities import router as cities_router
from app.api.v1.public.doctors import router as doctors_router
from app.api.v1.public.events import router as events_router
from app.api.v1.public.faq import router as faq_router
from app.api.v1.public.org_docs import router as org_docs_router
from app.api.v1.public.seo import router as seo_router
from app.api.v1.public.settings import router as settings_router

router = APIRouter()

router.include_router(settings_router)
router.include_router(cities_router)
router.include_router(doctors_router)
router.include_router(events_router)
router.include_router(articles_router)
router.include_router(org_docs_router)
router.include_router(seo_router)
router.include_router(certificates_router)
router.include_router(faq_router)
