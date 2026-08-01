from app.routers.documents import router as documents_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router

__all__ = [
    "documents_router",
    "chat_router",
    "conversations_router",
    "analytics_router",
    "auth_router",
]
