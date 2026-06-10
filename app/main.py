from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.sql_validate import router as sql_validate_router
from app.routes.ai_query import router as ai_query_router
from app.routes.ai_history import router as ai_history_router
from app.routes.page_insights import router as page_insights_router
from app.routes.entity_insights import router as entity_insights_router
from app.routes.rag import router as rag_router

app = FastAPI(title="Smart Lighting AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
