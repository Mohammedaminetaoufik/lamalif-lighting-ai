from fastapi import APIRouter

router = APIRouter()


@router.get("/ai/schema")
def ai_schema():
    return {"message": "AI schema endpoint not implemented yet", "status": "todo"}
