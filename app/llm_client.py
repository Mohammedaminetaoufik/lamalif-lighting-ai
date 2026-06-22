import json

from openai import OpenAI
from groq import Groq

from app.config import settings
from app.prompt_builder import build_sql_prompt
from app.rag.schemas import RAGContext

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

_SYSTEM_MSG = (
    "Tu es un expert SQL spécialisé dans les systèmes de télégestion d'éclairage public intelligent (smart city). "
    "Tu connais parfaitement le schéma de la plateforme Lamalif : lampadaires connectés, LCUs (passerelles radio), "
    "alertes terrain, bons de travail, télémétrie capteurs (température, puissance, tension, courant), mise en service. "
    "Tu génères UNIQUEMENT du SQL PostgreSQL SELECT valide sur les vues autorisées. "
    "Aucun markdown, aucune explication, SQL brut uniquement."
)

class LLMConfigurationError(Exception):
    pass


# Clients singletons — évite de recréer la connexion TLS à chaque appel
_groq_client: Groq | None = None
_openai_client: OpenAI | None = None


def _get_groq_client() -> Groq:
    global _groq_client
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise LLMConfigurationError("GROQ_API_KEY is not configured")
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def _get_openai_client() -> OpenAI:
    global _openai_client
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        raise LLMConfigurationError("OPENAI_API_KEY is not configured")
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def clean_sql_output(content: str) -> str:
    sql = content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    sql = sql.rstrip(";").strip()
    return sql


def generate_sql_with_openai(question: str, rag: RAGContext | None = None, history: list[dict] | None = None) -> str:
    from app.rag.context_builder import format_rag_for_sql_prompt
    rag_section = format_rag_for_sql_prompt(rag) if rag else ""
    client = _get_openai_client()
    prompt = build_sql_prompt(question, rag_context=rag_section)

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_MSG}]
    if history:
        # Inject last 4 messages (2 exchanges) as context — helps SQL generation on follow-up questions
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=DEFAULT_OPENAI_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=600,
    )

    content = response.choices[0].message.content or ""
    return clean_sql_output(content)


def generate_sql_with_groq(question: str, rag: RAGContext | None = None, history: list[dict] | None = None) -> str:
    from app.rag.context_builder import format_rag_for_sql_prompt
    rag_section = format_rag_for_sql_prompt(rag) if rag else ""
    client = _get_groq_client()
    prompt = build_sql_prompt(question, rag_context=rag_section)

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_MSG}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0,
        max_tokens=600,
    )

    content = response.choices[0].message.content or ""
    return clean_sql_output(content)


def generate_sql_with_llm(question: str, rag: RAGContext | None = None, history: list[dict] | None = None) -> str:
    provider = settings.llm_provider.lower().strip()

    if provider == "groq":
        return generate_sql_with_groq(question, rag=rag, history=history)

    if provider == "openai":
        return generate_sql_with_openai(question, rag=rag, history=history)

    raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


_PROFESSIONAL_SYSTEM = (
    "Tu es Lamalif IA, expert senior en télégestion d'éclairage public intelligent. "
    "Tu maîtrises : les protocoles DALI/D4i/0-10V, les LCUs (passerelles radio LoRa/Zigbee), les drivers LED, "
    "la maintenance prédictive, la gestion des alertes et des bons de travail terrain. "
    "Tu analyses des données PostgreSQL réelles et tu produis des réponses structurées, précises et actionnables. "
    "Tu distingues toujours : urgences terrain (offline, alertes critiques), optimisations (énergie, dimming), "
    "et constats sans action immédiate. Tu réponds en français professionnel, avec des chiffres précis et des noms réels. "
    "Tu génères une réponse en deux sections séparées par ---CHAT---.\n\n"
    "RÈGLES ABSOLUES pour les calculs et formules :\n"
    "- Si le contexte RAG contient la formule, cite-la explicitement dans ta réponse.\n"
    "- Explique toujours les variables utilisées dans la formule.\n"
    "- Indique si le résultat est une ESTIMATION et non une mesure exacte.\n"
    "- Si les données proviennent du simulateur, précise-le.\n"
    "- Ne présente JAMAIS un score heuristique comme une probabilité statistique entraînée.\n"
    "- N'affirme JAMAIS que le système utilise du machine learning si le calcul est rule-based.\n"
    "- Ne recalcule JAMAIS une valeur si elle est déjà fournie dans les résultats SQL.\n"
    "- N'invente JAMAIS un tarif kWh, un facteur CO₂ ou un seuil absent du contexte.\n"
    "- Si un paramètre est configurable (tarif, facteur CO₂), précise-le.\n"
    "- Pour les questions sur les calculs, structure la réponse avec : "
    "### Résultat | ### Formule utilisée | ### Interprétation métier | ### Limites / hypothèses."
)

_VALID_PRIORITIES = {"low", "medium", "high", "critical"}

_CHAT_SEPARATOR = "---CHAT---"


def generate_professional_answer(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[dict],
    rag: RAGContext | None = None,
    history: list[dict] | None = None,
) -> dict:
    client = _get_groq_client()

    # Cap context size — never send more than 50 rows to the LLM
    from app.rag.context_builder import format_rag_for_answer_prompt
    rag_section = format_rag_for_answer_prompt(rag) if rag else ""
    rows_sample = rows[:50]
    rows_str = json.dumps(rows_sample, ensure_ascii=False)
    columns_str = ", ".join(columns) if columns else "aucune colonne"

    # Detect calculation-type questions to apply the structured formula format
    _calcul_kw = (
        "calcul", "formule", "énergie", "energie", "kwh", "coût", "cout", "tarif",
        "économie", "economie", "co2", "co₂", "dimming", "intensité", "intensite",
        "score", "seuil", "alerte", "température", "temperature", "risque", "priorité",
        "priorite", "cause probable", "probabilité", "probabilite", "maintenabilité",
    )
    is_calcul_question = any(kw in question.lower() for kw in _calcul_kw)

    if is_calcul_question:
        calcul_instruction = (
            "\nCette question porte sur un CALCUL ou une FORMULE. "
            "Structure OBLIGATOIREMENT ta réponse Markdown ainsi :\n"
            "### Résultat\n[Valeur calculée en gras]\n"
            "### Formule utilisée\n[Formule en bloc de code si disponible dans le contexte RAG]\n"
            "### Interprétation métier\n[Ce que le résultat signifie pour l'opérateur]\n"
            "### Limites / hypothèses\n[Ce qui peut rendre ce résultat imprécis ou estimatif]\n"
            "### Action recommandée\n[Ce que l'opérateur doit faire]\n"
            "Ne présente JAMAIS un score heuristique comme une probabilité statistique. "
            "Mentionne si le tarif ou le facteur CO₂ est configurable."
        )
    else:
        calcul_instruction = ""

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
- Pour les calculs et formules : citer la formule depuis le contexte RAG si disponible, expliquer les variables, indiquer les limites.{calcul_instruction}

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
        # Thread last 6 messages (3 exchanges) so the LLM knows the conversation context
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2000,
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
    client = _get_groq_client()

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
        temperature=0.3,
        max_tokens=800,
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
    client = _get_groq_client()

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
                "content": (
                    "Tu es Lamalif IA, expert en diagnostic d'équipements d'éclairage public intelligent. "
                    "Tu analyses les données techniques d'un lampadaire ou d'une LCU (passerelle radio) "
                    "et produis un diagnostic précis, technique et actionnable pour l'administrateur. "
                    "Retourne uniquement du JSON valide sur une seule ligne."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
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


def generate_doc_answer(
    question: str,
    rag: RAGContext | None = None,
    history: list[dict] | None = None,
) -> dict:
    """
    Answer a documentation / formula question purely from RAG context.
    No SQL is generated or executed. Used when the question asks HOW something
    is calculated rather than asking for a live data value.
    """
    client = _get_groq_client()

    from app.rag.context_builder import format_rag_for_answer_prompt
    rag_section = format_rag_for_answer_prompt(rag) if rag else ""

    prompt = f"""Tu es un expert senior en télégestion d'éclairage public intelligent (plateforme Lamalif).

L'administrateur pose une question sur la MÉTHODOLOGIE, une FORMULE ou un CALCUL du système :
{question}

INSTRUCTION CRITIQUE :
- Cette question ne demande PAS des données temps réel — elle demande COMMENT le système fonctionne.
- Ne cherche PAS dans la base de données. Il n'y a pas de résultats SQL ici.
- Réponds UNIQUEMENT à partir du contexte de documentation RAG ci-dessous.
- Si la formule est dans le contexte RAG, cite-la EXACTEMENT en bloc de code.
- Si le contexte ne contient pas la réponse, dis-le honnêtement sans inventer.
- Ne recalcule PAS de valeurs depuis des données fictives.
- Ne mentionne PAS de "résultats SQL" ni de "données disponibles".

{rag_section}
Retourne ta réponse en DEUX sections séparées EXACTEMENT par la ligne ---CHAT--- :

SECTION 1 — JSON compact sur UNE SEULE LIGNE :
{{"summary": "Résumé en 1-2 phrases.", "analysis": "Explication de la formule/méthodologie en 3-5 phrases.", "recommendation": "Ce que l'administrateur doit retenir.", "priority": "low", "confidence": 0.85}}

---CHAT---

SECTION 2 — Réponse structurée en Markdown (utilise ### pour chaque section) :

### Formule utilisée
[La formule exacte en bloc de code, copiée du contexte RAG]

### Explication des variables
[Explique chaque variable de la formule]

### Interprétation métier
[Ce que cette formule signifie pour l'opérateur du réseau]

### Limites / hypothèses
[Quelles hypothèses sont faites, pourquoi c'est une estimation si c'est le cas]

### Action recommandée
[Ce que l'administrateur doit savoir ou faire]

Règles absolues : ne jamais présenter un score heuristique comme une probabilité statistique.
Si un tarif ou un facteur (CO₂, kWh) est configurable, le préciser explicitement."""

    messages: list[dict] = [{"role": "system", "content": _PROFESSIONAL_SYSTEM}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2000,
    )

    content = (response.choices[0].message.content or "").strip()

    if content.startswith("```"):
        lines = content.splitlines()
        lines = [ln for ln in lines if not ln.startswith("```")]
        content = "\n".join(lines).strip()

    chat_response: str | None = None
    parsed: dict = {}
    if _CHAT_SEPARATOR in content:
        json_part, chat_part = content.split(_CHAT_SEPARATOR, 1)
        try:
            parsed = json.loads(json_part.strip())
        except Exception:
            s = json_part.find("{")
            e = json_part.rfind("}") + 1
            parsed = json.loads(json_part[s:e]) if s >= 0 and e > s else {}
        chat_response = chat_part.strip() or None
    else:
        try:
            parsed = json.loads(content.strip())
        except Exception:
            parsed = {
                "summary": "Réponse documentaire disponible.",
                "analysis": "",
                "recommendation": "",
                "priority": "low",
                "confidence": 0.8,
            }

    parsed["chat_response"] = chat_response

    if parsed.get("priority") not in _VALID_PRIORITIES:
        parsed["priority"] = "low"

    try:
        parsed["confidence"] = float(parsed.get("confidence", 0.85))
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.85

    return parsed


def generate_daily_digest(kpis: dict, rag: RAGContext | None = None) -> dict:
    client = _get_groq_client()

    from app.rag.context_builder import format_rag_for_insight_prompt
    rag_section = format_rag_for_insight_prompt(rag) if rag else ""
    data_str = json.dumps(kpis, ensure_ascii=False, default=str)

    prompt = f"""Tu es un assistant IA d'aide à la décision pour une plateforme de télégestion d'éclairage public intelligent.

Ta mission est de produire une "Synthèse Quotidienne" (Daily Digest) basée sur les KPIs des dernières 24 heures.

Données du réseau (24h) :
{data_str}

Contraintes strictes :
- Ne jamais inventer de chiffres ou informations absentes des données.
- Utiliser uniquement les données fournies.
- summary : 1-2 phrases de synthèse globale très claires.
- analysis : 3-5 phrases d'analyse métier (santé du réseau, points d'attention).
- recommendations : liste de 2 à 4 actions prioritaires pour la journée.
- priority : low | medium | high | critical
- confidence : float 0.0-1.0

{rag_section}
Retourne UNIQUEMENT un JSON valide sur UNE SEULE LIGNE (pas de retour à la ligne) :
{{"summary":"...","analysis":"...","recommendations":["...","..."],"priority":"medium","confidence":0.9}}"""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es Lamalif IA, expert en exploitation de réseaux d'éclairage public intelligent. "
                    "Tu produis chaque jour une synthèse claire et actionnelle de l'état du réseau "
                    "sur les dernières 24 heures, en te basant exclusivement sur les KPIs fournis. "
                    "Retourne uniquement du JSON valide sur une seule ligne."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
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
        parsed["confidence"] = float(parsed.get("confidence", 0.9))
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.9

    if not isinstance(parsed.get("recommendations"), list):
        recs = parsed.get("recommendations", "")
        parsed["recommendations"] = [recs] if recs else ["Surveillez les alertes critiques aujourd'hui."]

    return parsed
