from fastapi import APIRouter

from .auth import router as auth_router
from .tenants import router as tenants_router
from .users import router as users_router
from .posts import router as posts_router
from .media import router as media_router
from .social import router as social_router
from .scheduling import router as scheduling_router
from .analytics import router as analytics_router
from .dashboard import router as dashboard_router
from .ai import router as ai_router
from .workflows import router as workflows_router
from .webhooks import router as webhooks_router
from .pipelines import router as pipelines_router
from .automation import router as automation_router
from .moderation import router as moderation_router
from .news_items import router as news_items_router
from .channel_groups import router as channel_groups_router
from .scraper import router as scraper_router
from .template_assignments import router as template_assignments_router
from .templates import router as templates_router
from .external_news import router as external_news_router
from .drafts import router as drafts_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(users_router)
api_router.include_router(posts_router)
api_router.include_router(media_router)
api_router.include_router(social_router)
api_router.include_router(scheduling_router)
api_router.include_router(analytics_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_router)
api_router.include_router(workflows_router)
api_router.include_router(webhooks_router)
api_router.include_router(pipelines_router)
api_router.include_router(automation_router)
api_router.include_router(moderation_router)
api_router.include_router(news_items_router)
api_router.include_router(channel_groups_router)
api_router.include_router(scraper_router)
api_router.include_router(template_assignments_router)
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(external_news_router)
api_router.include_router(drafts_router)