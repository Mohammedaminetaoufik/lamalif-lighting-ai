from fastapi import APIRouter
from app.config import settings
from app.db import test_connection, execute_select

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@router.get("/health/db")
def health_db():
    return test_connection()


@router.get("/health/views")
def health_views():
    result = execute_select("SELECT COUNT(*) AS total FROM ai_lampadaire_status")
    return {
        "status": "ok",
        "view": "ai_lampadaire_status",
        "result": result,
    }


@router.get("/health/views/all")
def health_views_all():
    results = []
    errors = []

    for view in settings.allowed_views_list:
        try:
            rows = execute_select(f"SELECT COUNT(*) AS total FROM {view}")
            count = rows[0]["total"] if rows else 0
            results.append({"view": view, "status": "ok", "count": count})
        except Exception as exc:
            errors.append({"view": view, "status": "error", "error": str(exc)})

    if not errors:
        overall = "ok"
    elif results:
        overall = "degraded"
    else:
        overall = "error"
    return {
        "status": overall,
        "total_views": len(settings.allowed_views_list),
        "ok_count": len(results),
        "error_count": len(errors),
        "views": results,
        "errors": errors,
    }
