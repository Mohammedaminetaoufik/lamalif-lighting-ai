from fastapi import APIRouter, Query
from app.db import get_ai_query_history

router = APIRouter(prefix="/ai", tags=["AI History"])


@router.get("/history")
def ai_history(limit: int = Query(default=20, ge=1, le=100)):
    return get_ai_query_history(limit=limit)
