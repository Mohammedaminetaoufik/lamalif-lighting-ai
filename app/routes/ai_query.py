import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas import AIQueryRequest, AIQueryResponse, ChartSpec, RAGInfo
from app.llm_client import (
    generate_sql_with_llm, generate_professional_answer,
    generate_sql_with_groq, LLMConfigurationError,
    _PROFESSIONAL_SYSTEM, _get_groq_client,
)
from app.config import settings
from app.rag import build_rag_context
from app.sql_guard import validate_sql, SQLValidationError
from app.db import execute_select, log_ai_query
from app.recommendation_engine import (
    generate_basic_summary,
    rule_based_recommendation,
    infer_chart_type,
)
from app.prompt_builder import build_sql_prompt

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

    # Normalise conversation history to plain dicts (Pydantic models → dict)
    history: list[dict] | None = None
    if body.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in body.conversation_history]

    # Step 1 — Generate SQL with LLM (RAG context + conversation history injected)
    try:
        raw_sql = generate_sql_with_llm(body.question, rag=rag, history=history)
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
            history=history,
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


@router.post("/query/stream")
def ai_query_stream(body: AIQueryRequest):
    """
    Streaming variant of /ai/query.
    Steps 1-3 (SQL gen, validation, DB) are synchronous.
    Step 4 (answer) streams token-by-token via SSE.
    SSE events:
      - data: {"type":"meta", ...}   — JSON with sql/columns/rows/summary/priority/confidence
      - data: <token>                — each chat_response token
      - data: [DONE]                 — end of stream
    """
    start = time.time()

    rag = build_rag_context(body.question)
    history: list[dict] | None = None
    if body.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in body.conversation_history]

    # Step 1 — SQL generation
    try:
        raw_sql = generate_sql_with_llm(body.question, rag=rag, history=history)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "rate_limit" in err_str.lower():
            raise HTTPException(status_code=429, detail="Limite de tokens IA atteinte. Réessayez dans quelques minutes.")
        raise HTTPException(status_code=500, detail=f"Erreur IA : {err_str}")

    # Step 2 — SQLGuard
    try:
        safe_sql = validate_sql(raw_sql)
    except SQLValidationError as exc:
        raise HTTPException(status_code=400, detail=f"SQLGuard a bloqué la requête : {exc}")

    # Step 3 — DB execution
    try:
        result = execute_select(safe_sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur d'exécution SQL : {exc}")

    columns: list[str] = result["columns"]
    rows: list[dict] = result["rows"]
    chart_data = infer_chart_type(columns, rows)

    # Build answer prompt (reuse logic from generate_professional_answer)
    from app.rag.context_builder import format_rag_for_answer_prompt
    rag_section = format_rag_for_answer_prompt(rag) if rag else ""
    rows_sample = rows[:50]
    rows_str = json.dumps(rows_sample, ensure_ascii=False)
    columns_str = ", ".join(columns) if columns else "aucune colonne"

    answer_prompt = f"""Tu es un assistant d'aide à la décision pour une plateforme de télégestion d'éclairage public intelligent.

L'administrateur a posé cette question :
{body.question}

La requête SQL sécurisée exécutée est :
{safe_sql}

Colonnes retournées :
{columns_str}

Résultats retournés ({len(rows)} ligne(s) au total, {len(rows_sample)} affichée(s)) :
{rows_str}

Contraintes strictes :
- Ne jamais inventer de chiffres ni d'informations absentes des résultats.
- Ne jamais proposer d'action automatique sans validation humaine.
- Si les données montrent une concentration d'anomalies sur une LCU, le signaler clairement.
- Si des lampadaires sont hors ligne, recommander de vérifier la LCU avant d'envoyer des techniciens.
- Si les alertes sont critiques, recommander la priorisation des interventions.
- Si les résultats sont vides, expliquer qu'aucun résultat n'a été trouvé.

{rag_section}
Retourne ta réponse en DEUX sections séparées EXACTEMENT par la ligne ---CHAT--- :

SECTION 1 — JSON compact sur UNE SEULE LIGNE (pas de retours à la ligne dans les valeurs) :
{{"summary": "Résumé en 1-2 phrases.", "analysis": "Analyse métier en 3-5 phrases.", "recommendation": "Recommandation claire.", "priority": "low|medium|high|critical", "confidence": 0.8}}

---CHAT---

SECTION 2 — Réponse conversationnelle en Markdown (500 mots max) :
Réponds directement à la question comme un expert qui connaît ce réseau. Structure ta réponse ainsi :
- **Constat principal** : la valeur clé ou le chiffre le plus important en gras dès la première phrase
- Utilise ### pour les sous-sections si plusieurs angles sont nécessaires
- Listes `- ` pour énumérer équipements, zones ou actions
- Tableau Markdown si les données comportent 3+ colonnes utiles (uniquement les colonnes pertinentes)
- **Conclusion actionnable** : ce que l'administrateur doit faire maintenant, en une phrase claire
Intègre les vrais noms (zones, références LCU, codes lampadaires) depuis les résultats. Pas de h1. Pas de phrase générique d'intro type "Voici les résultats"."""

    messages: list[dict] = [{"role": "system", "content": _PROFESSIONAL_SYSTEM}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": answer_prompt})

    duration_ms = int((time.time() - start) * 1000)

    def event_stream():
        client = _get_groq_client()
        # Buffer JSON section before streaming chat_response
        json_buf = ""
        chat_started = False
        _SEPARATOR = "---CHAT---"

        try:
            stream = client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )

            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if not token:
                    continue

                if not chat_started:
                    json_buf += token
                    if _SEPARATOR in json_buf:
                        parts = json_buf.split(_SEPARATOR, 1)
                        json_raw = parts[0].strip()
                        remainder = parts[1].strip()
                        # Parse JSON section and emit meta event
                        try:
                            parsed = json.loads(json_raw)
                        except Exception:
                            # Try extracting JSON object from buffer
                            s = json_raw.find("{"); e = json_raw.rfind("}") + 1
                            parsed = json.loads(json_raw[s:e]) if s >= 0 and e > s else {}

                        meta = {
                            "type": "meta",
                            "sql": safe_sql,
                            "columns": columns,
                            "rows": rows,
                            "summary": parsed.get("summary", ""),
                            "analysis": parsed.get("analysis", ""),
                            "recommendation": parsed.get("recommendation", ""),
                            "priority": parsed.get("priority", "medium"),
                            "confidence": float(parsed.get("confidence", 0.8)),
                            "chart": chart_data,
                            "execution_time_ms": duration_ms,
                        }
                        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

                        chat_started = True
                        if remainder:
                            yield f"data: {remainder}\n\n"
                else:
                    yield f"data: {token}\n\n"

        except Exception as exc:
            err = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(err)}\n\n"

        yield "data: [DONE]\n\n"
        safe_log(body.question, safe_sql, "success", row_count=result["row_count"], duration_ms=duration_ms)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
