from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.health import router as health_router
from app.routes.sql_validate import router as sql_validate_router
from app.routes.ai_query import router as ai_query_router
from app.routes.ai_history import router as ai_history_router
from app.routes.page_insights import router as page_insights_router
from app.routes.entity_insights import router as entity_insights_router
from app.routes.rag import router as rag_router
from app.routes.suggestions import router as suggestions_router
from app.routes.daily_digest import router as daily_digest_router
from app.routes.decision_center import router as decision_center_router
from app.routes.mobile_ai import router as mobile_ai_router

app = FastAPI(title="Smart Lighting AI Service")

# Origines limitées au backend Go + dev server Vite (configurable via CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "smart-lighting-ai",
        "status": "running",
    }


app.include_router(health_router)
app.include_router(sql_validate_router)
app.include_router(ai_query_router)
app.include_router(ai_history_router)
app.include_router(page_insights_router)
app.include_router(entity_insights_router)
app.include_router(rag_router)
app.include_router(suggestions_router)
app.include_router(daily_digest_router)
app.include_router(decision_center_router)
app.include_router(mobile_ai_router)
