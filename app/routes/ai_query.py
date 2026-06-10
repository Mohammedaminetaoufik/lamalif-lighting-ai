import time
from fastapi import APIRouter, HTTPException
from app.schemas import AIQueryRequest, AIQueryResponse, ChartSpec, RAGInfo
from app.llm_client import generate_sql_with_llm, generate_professional_answer, LLMConfigurationError
from app.rag import build_rag_context
from app.sql_guard import validate_sql, SQLValidationError
from app.db import execute_select, log_ai_query
from app.recommendation_engine import (
    generate_basic_summary,
    rule_based_recommendation,
    infer_chart_type,
)

router = APIRouter(prefix="/ai", tags=["AI Query"])


def safe_log(
    question: str,
    generated_sql: str | None,
    status: str,
    row_count: int = 0,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    try:
        log_ai_query(
            question=question,
            generated_sql=generated_sql,
            status=status,
            row_count=row_count,
            error_message=error_message,
            duration_ms=duration_ms,
            user_id=None,
        )
    except Exception:
        pass  # Logging failure must never break the main response


@router.post("/query", response_model=AIQueryResponse)
def ai_query(body: AIQueryRequest):
    start = time.time()
    raw_sql: str | None = None

    # Step 0 — Build RAG context (non-blocking, never raises)
    rag = build_rag_context(body.question)

    # Step 1 — Generate SQL with LLM (RAG context injected if available)
    try:
        raw_sql = generate_sql_with_llm(body.question, rag=rag)
    except LLMConfigurationError as exc:
        duration_ms = int((time.time() - start) * 1000)
        safe_log(body.question, None, "failed", error_message=str(exc), duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        safe_log(body.question, None, "failed", error_message=str(exc), duration_ms=duration_ms)
        err_str = str(exc)
        # Surface Groq / OpenAI rate-limit as 429 so the frontend can show a clear message
        if "429" in err_str or "rate_limit" in err_str.lower() or "rate limit" in err_str.lower():
            raise HTTPException(
                status_code=429,
                detail="Limite de tokens IA atteinte. Réessayez dans quelques minutes.",
            )
        raise HTTPException(status_code=500, detail=f"Erreur IA : {err_str}")

    # Step 2 — Validate with SQLGuard
    try:
        safe_sql = validate_sql(raw_sql)
    except SQLValidationError as exc:
        duration_ms = int((time.time() - start) * 1000)
        safe_log(body.question, raw_sql, "failed", error_message=str(exc), duration_ms=duration_ms)
        raise HTTPException(status_code=400, detail=f"SQLGuard a bloqué la requête : {exc}")

    # Step 3 — Execute against PostgreSQL
    try:
        result = execute_select(safe_sql)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        safe_log(body.question, safe_sql, "failed", error_message=str(exc), duration_ms=duration_ms)
        raise HTTPException(status_code=400, detail=f"Erreur d'exécution SQL : {exc}")
    columns: list[str] = result["columns"]
    rows: list[dict] = result["rows"]

    chart_data = infer_chart_type(columns, rows)

    # Step 4 — Generate professional answer with LLM (non-breaking fallback)
    try:
        professional = generate_professional_answer(
            question=body.question,
            sql=safe_sql,
            columns=columns,
            rows=rows,
            rag=rag,
        )
        summary = professional["summary"]
        analysis = professional.get("analysis", "Analyse détaillée indisponible pour le moment.")
        recommendation = professional["recommendation"]
        priority = professional.get("priority", "medium")
        confidence = professional.get("confidence", 0.8)
        chat_response = professional.get("chat_response")
    except Exception:
        summary = generate_basic_summary(body.question, rows)
        analysis = "Analyse détaillée indisponible pour le moment."
        recommendation = rule_based_recommendation(body.question, rows)
        priority = "medium"
        confidence = 0.7
        chat_response = None

    duration_ms = int((time.time() - start) * 1000)

    safe_log(
        body.question,
        safe_sql,
        "success",
        row_count=result["row_count"],
        duration_ms=duration_ms,
    )

    rag_info = RAGInfo(
        enabled=rag.enabled,
        used=rag.used,
        chunks_count=rag.chunks_count,
        sources=rag.sources,
    )

    return AIQueryResponse(
        question=body.question,
        sql=safe_sql,
        columns=columns,
        rows=rows,
        summary=summary,
        analysis=analysis,
        recommendation=recommendation,
        priority=priority,
        chat_response=chat_response,
        chart=ChartSpec(**chart_data),
        confidence=confidence,
        execution_time_ms=duration_ms,
        rag=rag_info,
    )
