import json

from openai import OpenAI
from groq import Groq

from app.config import settings
from app.prompt_builder import build_sql_prompt
from app.rag.schemas import RAGContext

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

_SYSTEM_MSG = "Tu génères uniquement du SQL PostgreSQL sécurisé. Aucun markdown, aucune explication."


class LLMConfigurationError(Exception):
    pass


def clean_sql_output(content: str) -> str:
    sql = content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    sql = sql.rstrip(";").strip()
    return sql


def generate_sql_with_openai(question: str, rag: RAGContext | None = None) -> str:
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        raise LLMConfigurationError("OPENAI_API_KEY is not configured")

    from app.rag.context_builder import format_rag_for_sql_prompt
    rag_section = format_rag_for_sql_prompt(rag) if rag else ""
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_sql_prompt(question, rag_context=rag_section)

    response = client.chat.completions.create(
        model=DEFAULT_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    return clean_sql_output(content)


def generate_sql_with_groq(question: str, rag: RAGContext | None = None) -> str:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise LLMConfigurationError("GROQ_API_KEY is not configured")

    from app.rag.context_builder import format_rag_for_sql_prompt
    rag_section = format_rag_for_sql_prompt(rag) if rag else ""
    client = Groq(api_key=settings.groq_api_key)
    prompt = build_sql_prompt(question, rag_context=rag_section)

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    return clean_sql_output(content)


def generate_sql_with_llm(question: str, rag: RAGContext | None = None) -> str:
    provider = settings.llm_provider.lower().strip()

    if provider == "groq":
        return generate_sql_with_groq(question, rag=rag)

    if provider == "openai":
        return generate_sql_with_openai(question, rag=rag)

    raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


_PROFESSIONAL_SYSTEM = (
    "Tu es un expert en télégestion d'éclairage public. "
    "Tu analyses des données PostgreSQL et produis une réponse en deux sections séparées par ---CHAT---."
)

_VALID_PRIORITIES = {"low", "medium", "high", "critical"}

_CHAT_SEPARATOR = "---CHAT---"


def generate_professional_answer(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[dict],
    rag: RAGContext | None = None,
) -> dict:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise LLMConfigurationError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)

    # Cap context size — never send more than 50 rows to the LLM
    from app.rag.context_builder import format_rag_for_answer_prompt
    rag_section = format_rag_for_answer_prompt(rag) if rag else ""
    rows_sample = rows[:50]
    rows_str = json.dumps(rows_sample, ensure_ascii=False)
    columns_str = ", ".join(columns) if columns else "aucune colonne"

    prompt = f"""Tu es un assistant d'aide à la décision pour une plateforme de télégestion d'éclairage public intelligent.

L'administrateur a posé cette question :
{question}

La requête SQL sécurisée exécutée est :
{sql}

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
- Si les résultats concernent la consommation, recommander une analyse avec validation humaine.
- Si les résultats sont vides, expliquer qu'aucun résultat n'a été trouvé.

{rag_section}
Retourne ta réponse en DEUX sections séparées EXACTEMENT par la ligne ---CHAT--- :

SECTION 1 — JSON compact sur UNE SEULE LIGNE (pas de retours à la ligne dans les valeurs) :
{{"summary": "Résumé en 1-2 phrases.", "analysis": "Analyse métier en 3-5 phrases.", "recommendation": "Recommandation claire.", "priority": "low|medium|high|critical", "confidence": 0.8}}

---CHAT---

SECTION 2 — Réponse conversationnelle en Markdown (200 mots max) :
Réponds directement à la question de façon naturelle. Utilise **gras** pour les valeurs clés, des listes - pour énumérer. Intègre les vrais chiffres et noms des résultats. Pas de titre h1. Sous-sections ### autorisées si nécessaire."""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _PROFESSIONAL_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = (response.choices[0].message.content or "").strip()

    # Strip outer markdown fences if present
    if content.startswith("```"):
        lines = content.splitlines()
        lines = [l for l in lines if not l.startswith("```")]
        content = "\n".join(lines).strip()

    # Split on the separator
    chat_response: str | None = None
    if _CHAT_SEPARATOR in content:
        json_part, chat_part = content.split(_CHAT_SEPARATOR, 1)
        parsed = json.loads(json_part.strip())
        chat_response = chat_part.strip() or None
    else:
        # Fallback: try plain JSON (no chat section)
        parsed = json.loads(content.strip())

    parsed["chat_response"] = chat_response

    if parsed.get("priority") not in _VALID_PRIORITIES:
        parsed["priority"] = "medium"

    try:
        parsed["confidence"] = float(parsed.get("confidence", 0.8))
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.8

    return parsed


def generate_page_insight(page: str, data: dict, rag: RAGContext | None = None) -> dict:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise LLMConfigurationError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)

    from app.rag.context_builder import format_rag_for_insight_prompt
    rag_section = format_rag_for_insight_prompt(rag) if rag else ""
    data_str = json.dumps(data, ensure_ascii=False, default=str)
    if len(data_str) > 8000:
        data_str = data_str[:8000] + "... [données tronquées]"

    prompt = f"""Tu es un assistant IA d'aide à la décision pour une plateforme de télégestion d'éclairage public intelligent.

Tu reçois les données agrégées de la page admin : {page}

Données :
{data_str}

Ta mission : Générer une analyse professionnelle en français pour l'administrateur.

Contraintes strictes :
- Ne jamais inventer de chiffres ou informations absentes des données.
- Utiliser uniquement les données fournies.
- summary : 1-2 phrases de synthèse.
- analysis : 3-4 phrases d'analyse métier.
- recommendations : liste de 2 à 4 actions opérationnelles concrètes.
- Ne jamais proposer d'action destructive ou automatique sans validation humaine.
- Ne jamais proposer de modifier le dimming automatiquement.
- Si les données montrent des anomalies concentrées sur une LCU, le signaler clairement.
- Si des alertes critiques existent, recommander la priorisation immédiate.
- priority : low | medium | high | critical
- confidence : float 0.0-1.0

{rag_section}
Retourne UNIQUEMENT un JSON valide sur UNE SEULE LIGNE (pas de retour à la ligne) :
{{"summary":"...","analysis":"...","recommendations":["...","..."],"priority":"medium","confidence":0.85}}"""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": "Tu analyses des données de télégestion d'éclairage public. Retourne uniquement du JSON valide sur une seule ligne.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = (response.choices[0].message.content or "").strip()

    # Strip markdown fences
    if content.startswith("```"):
        lines = content.splitlines()
        lines = [ln for ln in lines if not ln.startswith("```")]
        content = "\n".join(lines).strip()

    # Extract JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        content = content[start:end]

    parsed = json.loads(content)

    if parsed.get("priority") not in _VALID_PRIORITIES:
        parsed["priority"] = "medium"

    try:
        parsed["confidence"] = float(parsed.get("confidence", 0.8))
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.8

    if not isinstance(parsed.get("recommendations"), list):
        recs = parsed.get("recommendations", "")
        parsed["recommendations"] = [recs] if recs else ["Analysez régulièrement les données du réseau."]

    return parsed


def generate_entity_insight(entity_type: str, entity_id: int, data: dict, rag: RAGContext | None = None) -> dict:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise LLMConfigurationError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)

    from app.rag.context_builder import format_rag_for_insight_prompt
    rag_section = format_rag_for_insight_prompt(rag) if rag else ""
    data_str = json.dumps(data, ensure_ascii=False, default=str)
    if len(data_str) > 7000:
        data_str = data_str[:7000] + "... [données tronquées]"

    prompt = f"""Tu es un assistant IA d'aide à la décision pour une plateforme de télégestion d'éclairage public intelligent.

Tu reçois les données techniques d'un équipement.

Type : {entity_type}
ID   : {entity_id}

Données :
{data_str}

Ta mission : Produire une analyse professionnelle en français pour l'administrateur.

Contraintes strictes :
- Ne jamais inventer de données ou de valeurs absentes.
- Utiliser uniquement les données fournies.
- Si une donnée est absente, le mentionner clairement.
- Ne jamais proposer d'action destructive ou automatique sans validation humaine.
- Ne jamais modifier le dimming automatiquement.
- summary : 1-2 phrases de synthèse concises.
- analysis : analyse technique détaillée de 3-4 phrases.
- recommendation : recommandation opérationnelle claire et actionnable.
- priority : low | medium | high | critical
- suggested_actions : liste de 2 à 4 actions terrain concrètes.
- confidence : float 0.0-1.0

{rag_section}
Retourne UNIQUEMENT un JSON valide sur UNE SEULE LIGNE :
{{"summary":"...","analysis":"...","recommendation":"...","priority":"medium","suggested_actions":["...","..."],"confidence":0.85}}"""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": "Tu analyses des équipements d'éclairage public intelligent. Retourne uniquement du JSON valide sur une seule ligne.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = (response.choices[0].message.content or "").strip()

    if content.startswith("```"):
        lines = content.splitlines()
        lines = [ln for ln in lines if not ln.startswith("```")]
        content = "\n".join(lines).strip()

    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        content = content[start:end]

    parsed = json.loads(content)

    if parsed.get("priority") not in _VALID_PRIORITIES:
        parsed["priority"] = "medium"

    try:
        parsed["confidence"] = float(parsed.get("confidence", 0.8))
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.8

    if not isinstance(parsed.get("suggested_actions"), list):
        sa = parsed.get("suggested_actions", "")
        parsed["suggested_actions"] = [sa] if sa else ["Vérifiez régulièrement l'état de l'équipement."]

    return parsed
