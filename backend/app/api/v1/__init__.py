"""API v1 package — aggregates all routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.content_admin import router as content_admin_router
from app.api.v1.content_blocks_admin import router as content_blocks_admin_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.doctors_admin import router as doctors_admin_router
from app.api.v1.events_admin import router as events_admin_router
from app.api.v1.notifications_admin import router as notifications_admin_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.payments_admin import router as payments_admin_router
from app.api.v1.profile import router as profile_router
from app.api.v1.public import router as public_router
from app.api.v1.seo_admin import router as seo_admin_router
from app.api.v1.settings_admin import router as settings_admin_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.voting import router as voting_router
from app.api.v1.users_admin import router as users_admin_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router, tags=["Auth"])
router.include_router(onboarding_router, tags=["Onboarding"])
router.include_router(profile_router, tags=["Profile"])
router.include_router(subscriptions_router, tags=["Subscriptions"])
router.include_router(certificates_router, tags=["Certificates"])
router.include_router(telegram_router, tags=["Telegram"])
router.include_router(voting_router, tags=["Voting"])
router.include_router(public_router, tags=["Public"])
router.include_router(events_admin_router, tags=["Admin - Events"])
router.include_router(content_admin_router, tags=["Admin - Content"])
router.include_router(content_blocks_admin_router, tags=["Admin - Content Blocks"])
router.include_router(settings_admin_router, tags=["Admin - Settings"])
router.include_router(doctors_admin_router, tags=["Admin - Doctors"])
router.include_router(payments_admin_router, tags=["Admin - Payments"])
router.include_router(dashboard_router, tags=["Admin - Dashboard"])
router.include_router(notifications_admin_router, tags=["Admin - Notifications"])
router.include_router(seo_admin_router, tags=["Admin - SEO"])
router.include_router(users_admin_router, tags=["Admin - Users"])
router.include_router(webhooks_router, tags=["Webhooks"])
