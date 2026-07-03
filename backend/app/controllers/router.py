from fastapi import APIRouter

from app.controllers.ai_routes import agents_router, chat_router, emails_router, search_router
from app.controllers.auth import router as auth_router
from app.controllers.crm_routes import (
    contacts_router,
    customers_router,
    deals_router,
    leads_router,
    notes_router,
)
from app.controllers.knowledge import documents_router, knowledge_router, rag_router, uploads_router
from app.controllers.operations import meetings_router, tasks_router, transcripts_router, workflows_router
from app.controllers.platform import (
    admin_router,
    analytics_router,
    dashboard_router,
    notifications_router,
    settings_router,
    users_router,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(customers_router)
api_router.include_router(contacts_router)
api_router.include_router(leads_router)
api_router.include_router(deals_router)
api_router.include_router(notes_router)
api_router.include_router(meetings_router)
api_router.include_router(transcripts_router)
api_router.include_router(tasks_router)
api_router.include_router(workflows_router)
api_router.include_router(documents_router)
api_router.include_router(knowledge_router)
api_router.include_router(rag_router)
api_router.include_router(uploads_router)
api_router.include_router(chat_router)
api_router.include_router(agents_router)
api_router.include_router(search_router)
api_router.include_router(emails_router)
api_router.include_router(analytics_router)
api_router.include_router(dashboard_router)
api_router.include_router(notifications_router)
api_router.include_router(settings_router)
api_router.include_router(admin_router)
