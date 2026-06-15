from fastapi import APIRouter, Query
from app.db import get_ai_query_history

router = APIRouter(prefix="/ai", tags=["AI History"])


@router.get("/history")
def ai_history(
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200)
):
    return get_ai_query_history(limit=limit, search=search)
