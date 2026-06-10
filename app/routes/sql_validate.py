from fastapi import APIRouter
from app.schemas import SQLValidateRequest, SQLValidateResponse
from app.sql_guard import validate_sql, SQLValidationError

router = APIRouter(tags=["SQL Guard"])


@router.post("/ai/sql/validate", response_model=SQLValidateResponse)
def sql_validate(body: SQLValidateRequest):
    try:
        safe_sql = validate_sql(body.sql)
        return SQLValidateResponse(valid=True, safe_sql=safe_sql, message="SQL valide")
    except SQLValidationError as e:
        return SQLValidateResponse(valid=False, error=str(e))
