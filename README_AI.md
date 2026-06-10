# README Technique — Smart Lighting AI Service

> Documentation technique du module IA de la plateforme **Lamalif Télégestion**.
> Service : `smart-lighting-ai` — FastAPI + PostgreSQL + Groq LLM + RAG.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture globale](#2-architecture-globale)
3. [Stack technique](#3-stack-technique)
4. [Structure des fichiers](#4-structure-des-fichiers)
5. [Configuration (.env)](#5-configuration-env)
6. [Sécurité — principes fondamentaux](#6-sécurité--principes-fondamentaux)
7. [Module SQLGuard](#7-module-sqlguard)
8. [Routes API disponibles](#8-routes-api-disponibles)
9. [Pipeline /ai/query — détail complet](#9-pipeline-aiquery--détail-complet)
10. [Module LLM (llm_client.py)](#10-module-llm-llm_clientpy)
11. [Module Prompt Builder](#11-module-prompt-builder)
12. [Vues PostgreSQL autorisées (ai_*)](#12-vues-postgresql-autorisées-ai_)
13. [Module RAG — architecture](#13-module-rag--architecture)
14. [RAG — pipeline d'ingestion](#14-rag--pipeline-dingestion)
15. [RAG — pipeline de récupération](#15-rag--pipeline-de-récupération)
16. [RAG — base de connaissances (rag_docs/)](#16-rag--base-de-connaissances-rag_docs)
17. [Schéma PostgreSQL RAG](#17-schéma-postgresql-rag)
18. [Page Insights et Entity Insights](#18-page-insights-et-entity-insights)
19. [Décisions techniques importantes](#19-décisions-techniques-importantes)
20. [Bugs corrigés et historique](#20-bugs-corrigés-et-historique)
21. [Commandes de déploiement](#21-commandes-de-déploiement)
22. [Tests API — commandes PowerShell](#22-tests-api--commandes-powershell)

---

## 1. Vue d'ensemble

Le service `smart-lighting-ai` est un microservice Python/FastAPI qui fournit :

- **Requêtes IA en langage naturel** : l'utilisateur pose une question en français, le service génère et exécute un SQL sécurisé, puis retourne une réponse rédigée.
- **Insights par page** : analyse automatique de chaque page admin (dashboard, lampadaires, LCUs, alertes, etc.).
- **Insights par équipement** : diagnostic IA individuel d'un lampadaire ou d'une LCU.
- **Module RAG** : enrichissement des réponses LLM avec de la documentation métier interne (règles, vues, exemples SQL).

Le service est appelé **uniquement par le backend Go**. Il n'est jamais exposé directement au frontend React.

```
React → Go (backend) → smart-lighting-ai (FastAPI) → PostgreSQL / Groq API
```

---

## 2. Architecture globale

```
┌─────────────────────────────────────────────────────────┐
│                   smart-lighting-ai                      │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────────┐  │
│  │ /ai/query│   │/ai/page- │   │/ai/entity-insights/ │  │
│  │          │   │insights/ │   │{type}/{id}          │  │
│  └────┬─────┘   └────┬─────┘   └──────────┬──────────┘  │
│       │              │                     │             │
│  ┌────▼──────────────▼─────────────────────▼──────────┐  │
│  │                  RAG (retriever)                    │  │
│  │   embed_query → search_jsonb → context_text         │  │
│  └────────────────────────┬────────────────────────────┘  │
│                           │                              │
│  ┌────────────────────────▼────────────────────────────┐  │
│  │              LLM Client (Groq / OpenAI)             │  │
│  │   generate_sql_with_llm()                           │  │
│  │   generate_professional_answer()                    │  │
│  │   generate_page_insight()                           │  │
│  │   generate_entity_insight()                         │  │
│  └────────────────────────┬────────────────────────────┘  │
│                           │                              │
│  ┌────────────────────────▼────────────────────────────┐  │
│  │                    SQLGuard                         │  │
│  │   sqlglot AST parsing — SELECT + vues ai_* seulement│  │
│  └────────────────────────┬────────────────────────────┘  │
│                           │                              │
│  ┌────────────────────────▼────────────────────────────┐  │
│  │              PostgreSQL (ai_readonly)               │  │
│  │   Vues ai_* uniquement — lecture seule              │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Runtime | Python | 3.12+ |
| Framework web | FastAPI | latest |
| Serveur ASGI | Uvicorn | standard |
| ORM / SQL | SQLAlchemy 2.0 | text() API |
| Driver PostgreSQL | psycopg (psycopg3) | binary |
| Validation config | pydantic-settings | v2 |
| LLM principal | Groq API (llama-3.3-70b-versatile) | — |
| LLM alternatif | OpenAI API (gpt-4.1-mini) | — |
| SQL parsing / sécurité | sqlglot | — |
| Embeddings | sentence-transformers | paraphrase-multilingual-MiniLM-L12-v2 |
| Calcul vectoriel | numpy | 2.x |
| Base de données | PostgreSQL | 14+ |
| Stockage vecteurs (optionnel) | pgvector | 0.4+ |

---

## 4. Structure des fichiers

```
smart-lighting-ai/
│
├── app/
│   ├── main.py                  # Application FastAPI + montage des routers
│   ├── config.py                # Settings pydantic-settings (lit .env)
│   ├── db.py                    # Engines SQLAlchemy (ai_readonly + ai_logger)
│   ├── schemas.py               # Modèles Pydantic partagés (Request/Response)
│   ├── sql_guard.py             # Module de validation SQL (SQLGuard)
│   ├── prompt_builder.py        # Construction des prompts SQL avec schéma + exemples
│   ├── llm_client.py            # Appels LLM (Groq, OpenAI) — 4 fonctions principales
│   ├── recommendation_engine.py # Fallback rule-based si LLM indisponible
│   │
│   ├── routes/
│   │   ├── health.py            # GET /health
│   │   ├── sql_validate.py      # POST /ai/sql-validate
│   │   ├── ai_query.py          # POST /ai/query  ← route principale
│   │   ├── ai_history.py        # GET /ai/history
│   │   ├── page_insights.py     # GET /ai/page-insights/{page}
│   │   ├── entity_insights.py   # GET /ai/entity-insights/{type}/{id}
│   │   └── rag.py               # POST /rag/ingest  GET /rag/status
│   │
│   └── rag/
│       ├── __init__.py          # Exporte build_rag_context
│       ├── schemas.py           # RAGContext, RAGChunk, IngestResult
│       ├── embeddings.py        # SentenceTransformer — embed_query(), cosine_similarity()
│       ├── chunking.py          # chunk_markdown(), chunk_text() avec overlap
│       ├── storage.py           # upsert_document(), insert_chunk(), search_jsonb()
│       ├── ingestion.py         # ingest_all() — orchestre tout le pipeline d'ingestion
│       ├── retriever.py         # build_rag_context(), search_rag()
│       └── context_builder.py   # Formatage du contexte RAG pour les prompts LLM
│
├── rag_docs/                    # Base de connaissances métier (Markdown)
│   ├── views_dictionary.md      # Toutes les vues ai_* avec colonnes et exemples SQL
│   ├── sql_examples.md          # Questions → SQL par catégorie
│   ├── business_rules.md        # Règles métier (zone critique, LCU avant lampadaires...)
│   ├── recommendation_rules.md  # Recommandations par situation
│   ├── smart_lighting_terms.md  # Vocabulaire domaine (LCU, dimming, D4i, DALI...)
│   ├── security_rules.md        # Règles sécurité SQL (SELECT only, données interdites)
│   ├── entity_diagnostics.md    # Méthodes de diagnostic lampadaire / LCU
│   └── page_insights_rules.md   # Règles d'analyse par page admin
│
├── sql/
│   ├── 04_rag_tables.sql         # Tables RAG version JSONB stable (sans pgvector)
│   └── 04_rag_tables_pgvector.sql # Extension optionnelle pgvector (ALTER TABLE)
│
├── scripts/
│   └── setup_rag_db.ps1         # Script PowerShell d'installation des tables RAG
│
├── .env                         # Variables d'environnement (ne pas committer)
├── .env.example                 # Template public sans secrets
├── requirements.txt             # Dépendances Python
└── README_AI.md                 # Ce fichier
```

---

## 5. Configuration (.env)

```env
# ── Service ───────────────────────────────────────────────
APP_NAME=smart-lighting-ai
PORT=8090

# ── PostgreSQL ────────────────────────────────────────────
# Lecture seule — vues ai_* uniquement
DATABASE_URL=postgresql+psycopg://ai_readonly:password@localhost:5432/lampadaire
# Écriture — ai_query_logs + tables RAG
LOG_DATABASE_URL=postgresql+psycopg://ai_logger:password@localhost:5432/lampadaire

# ── LLM ──────────────────────────────────────────────────
LLM_PROVIDER=groq                          # ou openai
GROQ_API_KEY=gsk_...                       # Clé Groq (ne jamais exposer)
GROQ_MODEL=llama-3.3-70b-versatile
OPENAI_API_KEY=sk-...                      # Clé OpenAI (optionnel)

# ── Sécurité SQL ─────────────────────────────────────────
MAX_ROWS=500
DEFAULT_LIMIT=100
SQL_TIMEOUT_SECONDS=5
ALLOWED_VIEWS=ai_lampadaire_status,ai_lcu_status,...  # liste exhaustive

# ── RAG ──────────────────────────────────────────────────
RAG_ENABLED=true
RAG_BACKEND=jsonb                          # jsonb (stable) ou pgvector (optionnel)
RAG_TOP_K=5                                # Nombre de chunks retournés par recherche
RAG_MAX_CONTEXT_CHARS=6000                 # Limite du contexte injecté dans le prompt
RAG_CHUNK_SIZE=1000                        # Taille maximale d'un chunk (caractères)
RAG_CHUNK_OVERLAP=150                      # Chevauchement entre chunks consécutifs
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
```

### Rôles PostgreSQL

| Rôle | Droits | Usage |
|---|---|---|
| `ai_readonly` | SELECT sur les vues `ai_*` | Exécution des requêtes générées par le LLM |
| `ai_logger` | SELECT/INSERT/UPDATE/DELETE sur `ai_query_logs`, `rag_documents`, `rag_chunks` | Logs + ingestion RAG |

---

## 6. Sécurité — principes fondamentaux

Ces règles sont **non négociables** et appliquées à plusieurs niveaux :

1. **Le LLM génère uniquement des SELECT** — vérifié par SQLGuard après chaque génération.
2. **Uniquement les vues `ai_*`** — les tables brutes (`lampadaires`, `users`, etc.) sont inaccessibles par `ai_readonly`.
3. **Pas de données sensibles** — `password`, `auth_token`, `api_key`, `.env` ne sont jamais dans les vues ni dans les prompts.
4. **Le RAG ne contourne pas SQLGuard** — le contexte RAG est injecté dans le prompt, mais SQLGuard valide toujours le SQL résultant.
5. **Aucune action automatique sur les équipements** — le LLM ne peut pas déclencher de dimming, de reboot ou de synchronisation.
6. **Les clés API ne transitent jamais par React ou Go** — elles restent dans le `.env` du service FastAPI uniquement.
7. **Validation humaine obligatoire** pour toute action terrain.

---

## 7. Module SQLGuard

**Fichier** : `app/sql_guard.py`

SQLGuard est la **dernière ligne de défense** avant l'exécution SQL. Il utilise `sqlglot` pour parser le SQL en AST et vérifie :

- **Type de statement** : uniquement `SELECT` autorisé
- **Tables sources** : uniquement les vues dont le nom commence par `ai_`
- **Mots-clés interdits** : `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `COPY`, `GRANT`, `REVOKE`, `EXECUTE`
- **Colonnes sensibles** : `password`, `password_hash`, `auth_token`, `token`, `api_key`, `secret`
- **Clause LIMIT** : ajoutée automatiquement si absente (défaut : 100)

```python
try:
    safe_sql = validate_sql(raw_sql)
except SQLValidationError as exc:
    raise HTTPException(400, detail=f"SQLGuard a bloqué la requête : {exc}")
```

SQLGuard est appliqué **après** la génération LLM et **avant** l'exécution PostgreSQL, dans tous les cas.

---

## 8. Routes API disponibles

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check minimal |
| GET | `/health` | Status détaillé avec test DB |
| POST | `/ai/query` | Question NL → SQL → réponse rédigée |
| POST | `/ai/sql-validate` | Valider un SQL brut via SQLGuard |
| GET | `/ai/history` | Historique des requêtes (ai_query_logs) |
| GET | `/ai/page-insights/{page}` | Analyse IA de la page admin |
| GET | `/ai/entity-insights/{type}/{id}` | Diagnostic IA d'un équipement |
| POST | `/rag/ingest` | Ingestion des documents `rag_docs/` |
| GET | `/rag/status` | Statut et métriques du module RAG |

### Pages supportées par `/ai/page-insights/{page}`

`dashboard`, `lampadaires`, `lcus`, `alerts`, `workorders`, `energy`, `commissioning`, `map`

### Types d'entité pour `/ai/entity-insights/{type}/{id}`

`lampadaire`, `lcu`

---

## 9. Pipeline /ai/query — détail complet

```
POST /ai/query
  { "question": "Quelle zone est la plus critique ?", "language": "fr" }
```

**Étape 0 — RAG context** (non-bloquant)
```python
rag = build_rag_context(body.question)
# → embed_query(question) → search_jsonb(embedding, top_k=5) → RAGContext
# Si RAG échoue → RAGContext(enabled=True, used=False) — pipeline continue
```

**Étape 1 — Génération SQL** (LLM)
```python
raw_sql = generate_sql_with_llm(body.question, rag=rag)
# Prompt = schéma des vues + exemples SQL + contexte RAG + question
# LLM retourne un SELECT brut
```

**Étape 2 — Validation SQLGuard**
```python
safe_sql = validate_sql(raw_sql)
# AST parsing sqlglot → bloque si non conforme
```

**Étape 3 — Exécution PostgreSQL**
```python
result = execute_select(safe_sql)
# Connexion ai_readonly → SELECT sur vues ai_* uniquement
```

**Étape 4 — Réponse professionnelle** (LLM, non-bloquant)
```python
professional = generate_professional_answer(question, sql, columns, rows, rag=rag)
# Retourne : summary, analysis, recommendation, priority, confidence, chat_response
# Si LLM échoue → fallback rule-based (recommendation_engine.py)
```

**Étape 5 — Log + réponse**
```python
log_ai_query(...)   # INSERT dans ai_query_logs
return AIQueryResponse(
    question, sql, columns, rows,
    summary, analysis, recommendation, priority,
    chat_response, chart, confidence, execution_time_ms,
    rag=RAGInfo(enabled, used, chunks_count, sources)
)
```

### Format de réponse AIQueryResponse

```json
{
  "question": "Quelle zone est la plus critique ?",
  "sql": "SELECT zone, offline_count, ... FROM ai_zone_health ORDER BY ...",
  "columns": ["zone", "offline_count", "critical_alerts_count"],
  "rows": [{"zone": "Agdal", "offline_count": 12, ...}],
  "summary": "La zone Agdal est la plus critique avec 12 lampadaires offline.",
  "analysis": "La concentration de pannes sur une même LCU suggère...",
  "recommendation": "Vérifier la LCU-04 en priorité avant d'envoyer des techniciens.",
  "priority": "high",
  "chat_response": "**Zone Agdal** : 12 lampadaires offline...",
  "chart": {"type": "bar", "x": "zone", "y": "offline_count"},
  "confidence": 0.87,
  "execution_time_ms": 1240,
  "rag": {
    "enabled": true,
    "used": true,
    "chunks_count": 3,
    "sources": ["Business Rules", "Sql Examples"]
  }
}
```

---

## 10. Module LLM (llm_client.py)

**Fichier** : `app/llm_client.py`

Quatre fonctions principales, toutes avec le paramètre optionnel `rag: RAGContext | None` :

| Fonction | Usage | LLM |
|---|---|---|
| `generate_sql_with_llm(question, rag)` | Génère un SELECT PostgreSQL | Groq ou OpenAI |
| `generate_professional_answer(question, sql, columns, rows, rag)` | Réponse rédigée en 2 sections (JSON + Markdown) | Groq |
| `generate_page_insight(page, data, rag)` | Analyse de page admin | Groq |
| `generate_entity_insight(entity_type, entity_id, data, rag)` | Diagnostic équipement | Groq |

### Format de réponse `generate_professional_answer`

Le LLM retourne deux sections séparées par `---CHAT---` :

```
{"summary":"...","analysis":"...","recommendation":"...","priority":"high","confidence":0.85}
---CHAT---
**Zone Agdal** : 12 lampadaires offline. La LCU-04 est hors ligne...
```

### Modèles LLM

- **Groq** : `llama-3.3-70b-versatile` (principal, défaut)
- **OpenAI** : `gpt-4.1-mini` (alternatif)
- Sélection via `LLM_PROVIDER=groq` ou `LLM_PROVIDER=openai`

### Gestion des erreurs LLM

- `LLMConfigurationError` : clé API absente → HTTP 500
- Rate limit (429) : HTTP 429 avec message clair pour le frontend
- Toute autre erreur sur `generate_professional_answer` → fallback `recommendation_engine.py` (rule-based)

---

## 11. Module Prompt Builder

**Fichier** : `app/prompt_builder.py`

```python
def build_sql_prompt(question: str, rag_context: str = "") -> str:
```

Le prompt injecté au LLM contient dans l'ordre :
1. **Instructions strictes** : SELECT seulement, vues `ai_*` seulement, LIMIT obligatoire
2. **Schéma complet** des 20 vues autorisées avec toutes leurs colonnes
3. **Exemples Q→SQL** couvrant tous les cas d'usage courants
4. **Contexte RAG** (optionnel) : chunks de documentation métier pertinents
5. **La question** de l'utilisateur

---

## 12. Vues PostgreSQL autorisées (ai_*)

20 vues en lecture seule, préfixées `ai_` :

| Vue | Données | Usage typique |
|---|---|---|
| `ai_global_kpis` | KPIs globaux (1 ligne) | Situation générale réseau |
| `ai_lampadaire_status` | État de chaque lampadaire | Online/offline/maintenance, intensité, LCU |
| `ai_lcu_status` | État des LCUs + compteurs | Lampadaires par LCU, last_seen |
| `ai_open_alerts` | Alertes ouvertes | Severity, message, cause probable |
| `ai_workorders` | Bons de travail | Status, priorité, technicien |
| `ai_telemetry_latest` | Dernière télémétrie | Température, puissance, courant |
| `ai_zone_health` | Santé par zone | offline_count, critical_alerts_count |
| `ai_energy_summary` | Consommation par zone | kWh, puissance moyenne |
| `ai_lampadaire_diagnostics` | Diagnostic technique | driver_temperature, fault_status |
| `ai_lcu_health` | Santé LCU avec health_score | Score 0-100 |
| `ai_workorder_age` | Bons de travail + ancienneté | age_hours |
| `ai_alert_summary` | Résumé alertes par zone/LCU | Agrégation par severity |
| `ai_commissioning_status` | Mise en service | test_comm, test_dimming |
| `ai_dimming_status` | Dimming par lampadaire | d4i_compatible, intensité courante |
| `ai_driver_health` | État driver LED | Températures, protection surtension |
| `ai_controller_network_status` | Signal contrôleur | controller_signal_quality |
| `ai_map_assets` | Assets cartographiques | GPS, has_location |
| `ai_recent_activity` | Activité récente 7j | Événements réseau |
| `ai_maintenance_overview` | Vue maintenance par zone | Interventions ouvertes/résolues |
| `ai_technician_workload` | Charge par technicien | open_count, in_progress_count |

---

## 13. Module RAG — architecture

Le RAG (Retrieval-Augmented Generation) enrichit les réponses LLM avec de la documentation métier.

**Principe :**
```
Question utilisateur
       ↓
embed_query()           → vecteur float[384]
       ↓
search_jsonb()          → top_k chunks similaires (cosine similarity Python/numpy)
       ↓
context_builder.py      → texte formaté pour injection dans prompt LLM
       ↓
build_sql_prompt()      → prompt final avec contexte RAG
```

**Règles de sécurité RAG :**
- Le RAG est du **contexte uniquement** — il ne génère pas de SQL.
- SQLGuard reste obligatoire après toute génération LLM incluant du contexte RAG.
- Si le RAG échoue → `RAGContext(used=False)` — le pipeline continue sans RAG.
- Le RAG ne contient aucune donnée sensible (pas de mots de passe, tokens, clés API).

### Fichiers du module RAG

```
app/rag/
├── __init__.py          → exporte build_rag_context
├── schemas.py           → RAGContext, RAGChunk, RAGDocument, IngestResult
├── embeddings.py        → SentenceTransformer lazy-loaded, cosine_similarity numpy
├── chunking.py          → chunk_markdown() split par ## puis par chunk_size
├── storage.py           → upsert_document(), insert_chunk(), search_jsonb()
├── ingestion.py         → ingest_all() orchestre rag_docs/ → PostgreSQL
├── retriever.py         → build_rag_context(), search_rag() API publique
└── context_builder.py   → format_rag_for_sql_prompt(), format_rag_for_insight_prompt()
```

---

## 14. RAG — pipeline d'ingestion

Déclenché par `POST /rag/ingest` ou `ingest_all(force=True)`.

```
rag_docs/*.md
     │
     ▼
_file_hash(content)      → SHA256 du fichier complet
     │
     ▼
upsert_document()         → INSERT ou UPDATE dans rag_documents
     │                      (skip si content_hash identique ET force=False)
     ▼
chunk_markdown()           → split par sections ## Markdown
     │                       puis chunk_text() si section > chunk_size
     │                       overlap configurable (défaut 150 chars)
     ▼
embed_texts()             → SentenceTransformer.encode() → float[384][]
     │                       (lazy loading du modèle au premier appel)
     │                       Si embedding échoue → None (chunk stocké sans vecteur)
     ▼
insert_chunk()            → INSERT INTO rag_chunks ... CAST(:ejson AS jsonb)
     │                       ON CONFLICT DO UPDATE
     ▼
delete_old_chunks()       → DELETE des chunks obsolètes (indices non présents)
```

**Résultat retourné :**
```json
{
  "documents_processed": 8,
  "chunks_created": 142,
  "chunks_updated": 0,
  "errors": []
}
```

### Stratégie de chunking

- **Découpage primaire** : sections Markdown (`## titre`)
- **Découpage secondaire** : si section > `RAG_CHUNK_SIZE` chars → découpage sliding window
- **Overlap** : `RAG_CHUNK_OVERLAP=150` chars — chevauchement pour préserver le contexte
- **Hash par chunk** : SHA256 du contenu → skip si inchangé (ingestion incrémentale)

---

## 15. RAG — pipeline de récupération

Déclenché à chaque appel `/ai/query`, `/ai/page-insights`, `/ai/entity-insights`.

```python
# Appel public
rag = build_rag_context(query="Quelle zone est la plus critique ?")

# Résultat
RAGContext(
    enabled=True,
    used=True,
    chunks_count=3,
    sources=["Business Rules", "Sql Examples", "Views Dictionary"],
    context_text="[Source: Business Rules]\nUne zone est critique si..."
)
```

### Mode JSONB (actuel, stable)

```python
# 1. Encoder la question
embedding = embed_query(query, model_name)       # float[384]

# 2. Charger tous les chunks depuis PostgreSQL
SELECT c.id, c.content, d.title, c.embedding_json
FROM rag_chunks c JOIN rag_documents d ON ...
WHERE c.embedding_json IS NOT NULL

# 3. Similarité cosine en Python
score = cosine_similarity(query_embedding, stored_embedding)
# np.dot(a, b) / (||a|| * ||b||)

# 4. Trier, filtrer, construire le contexte
chunks[:top_k] → context_text (limitée à RAG_MAX_CONTEXT_CHARS)
```

### Mode pgvector (optionnel, futur)

Disponible après exécution de `sql/04_rag_tables_pgvector.sql` et `RAG_BACKEND=pgvector` :
```sql
SELECT ..., 1 - (c.embedding <=> CAST(:emb AS vector)) AS score
FROM rag_chunks c ...
ORDER BY c.embedding <=> CAST(:emb AS vector)
LIMIT :k
```

---

## 16. RAG — base de connaissances (rag_docs/)

8 fichiers Markdown constituant la documentation métier injectée dans le RAG :

| Fichier | Contenu | Chunks approx. |
|---|---|---|
| `views_dictionary.md` | Toutes les vues `ai_*` avec colonnes détaillées et exemples SQL | ~40 |
| `sql_examples.md` | ~30 paires Question → SQL couvrant tous les cas d'usage | ~25 |
| `business_rules.md` | Règles métier : zone critique, LCU avant lampadaires, seuils temp | ~15 |
| `recommendation_rules.md` | Recommandations par situation (LCU offline, temp élevée, etc.) | ~15 |
| `smart_lighting_terms.md` | Glossaire : LCU, dimming, DALI, D4i, commissioning, health_score | ~12 |
| `security_rules.md` | SELECT seulement, données sensibles interdites, SQLGuard | ~8 |
| `entity_diagnostics.md` | Méthodes de diagnostic lampadaire et LCU, ordre d'analyse | ~12 |
| `page_insights_rules.md` | Points d'analyse clés par page admin, métriques à surveiller | ~15 |

---

## 17. Schéma PostgreSQL RAG

### Table `rag_documents`

```sql
CREATE TABLE rag_documents (
    id           SERIAL PRIMARY KEY,
    title        TEXT NOT NULL,
    source_type  TEXT NOT NULL,          -- 'markdown'
    source_path  TEXT,                   -- nom du fichier .md
    content      TEXT NOT NULL,          -- contenu brut
    content_hash TEXT NOT NULL,          -- SHA256 — détection changements
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(title, source_type)
);
```

### Table `rag_chunks`

```sql
CREATE TABLE rag_chunks (
    id             SERIAL PRIMARY KEY,
    document_id    INT REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index    INT NOT NULL,
    content        TEXT NOT NULL,
    content_hash   TEXT NOT NULL,        -- SHA256 — ingestion incrémentale
    embedding_json JSONB,                -- vecteur float[384] stocké en JSON
    metadata       JSONB DEFAULT '{}',
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);
```

### Colonnes ajoutées à `ai_query_logs`

```sql
ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_used         BOOLEAN DEFAULT false;
ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_chunks_count INT     DEFAULT 0;
ALTER TABLE ai_query_logs ADD COLUMN IF NOT EXISTS rag_sources      JSONB   DEFAULT '[]';
```

### Fichiers SQL

| Fichier | Description |
|---|---|
| `sql/04_rag_tables.sql` | Version stable JSONB — sans pgvector — à appliquer en premier |
| `sql/04_rag_tables_pgvector.sql` | Extension optionnelle — ajoute `embedding vector(384)` + index ivfflat |

---

## 18. Page Insights et Entity Insights

### Page Insights (`GET /ai/page-insights/{page}`)

Pour chaque page, un ensemble de requêtes SQL **prédéfinies** est exécuté (pas de génération LLM pour le SQL). Les données sont ensuite passées à `generate_page_insight()`.

- **Cache in-memory** : 5 minutes par page
- **Paramètre `?refresh=true`** : force la régénération

**Format de réponse :**
```json
{
  "page": "dashboard",
  "summary": "Réseau globalement stable...",
  "analysis": "3 zones présentent des alertes critiques...",
  "recommendations": ["Vérifier LCU-04", "Planifier maintenance zone Agdal"],
  "priority": "high",
  "kpis": {"total_lampadaires": 450, "offline_lampadaires": 12},
  "confidence": 0.85,
  "generated_at": "2025-06-10T14:23:11Z",
  "cached": false
}
```

### Entity Insights (`GET /ai/entity-insights/{type}/{id}`)

Collecte les données de l'équipement via des **requêtes paramétrées prédéfinies**, puis génère un diagnostic via `generate_entity_insight()`.

**Données collectées pour un lampadaire :**
- `ai_lampadaire_status` — état général
- `ai_lampadaire_diagnostics` — diagnostic technique
- `ai_telemetry_latest` — dernière télémétrie
- `ai_open_alerts` (filtré par `lampadaire_id`)
- `ai_workorders` (filtré par `lampadaire_id`)

**Données collectées pour une LCU :**
- `ai_lcu_status` + `ai_lcu_health` — état et score
- `ai_lampadaire_status` (filtré par `lcu_id`) — lampadaires rattachés
- `ai_open_alerts` + `ai_workorders` (filtré par `lcu_reference`)

**Priorité calculée** (rule-based avant LLM) :

| Lampadaire | LCU |
|---|---|
| `critical` si offline ou alertes critiques | `critical` si offline ou health_score < 30 |
| `high` si alertes ouvertes ou temp > 70°C | `high` si offline_count > 30% ou health_score < 60 |
| `medium` si en maintenance | `medium` si offline_count > 0 |
| `low` si tout nominal | `low` si health_score > 80 |

---

## 19. Décisions techniques importantes

### SQLAlchemy text() + psycopg3 — syntaxe CAST

**Problème** : La syntaxe PostgreSQL `:param::jsonb` est ambiguë pour le parser SQLAlchemy + psycopg3. Le driver convertit les autres paramètres en `$1, $2...` mais laisse `:param::jsonb` tel quel → erreur SQL.

**Solution adoptée** : Toujours utiliser `CAST(:param AS jsonb)` au lieu de `:param::jsonb`.

```python
# Incorrect avec psycopg3
"VALUES (:title, :chash, :meta::jsonb)"

# Correct
"VALUES (:title, :chash, CAST(:meta AS jsonb))"
```

Même règle pour pgvector : `CAST(:emb AS vector)` au lieu de `:emb::vector`.

### NOT IN avec SQLAlchemy text()

**Problème** : `text()` ne supporte pas le binding d'une liste Python directement.

**Solution** : Génération dynamique de placeholders individuels.

```python
placeholders = ", ".join(f":idx_{i}" for i in range(len(keep_indices)))
params = {"did": document_id}
params.update({f"idx_{i}": v for i, v in enumerate(keep_indices)})
conn.execute(text(f"DELETE ... WHERE chunk_index NOT IN ({placeholders})"), params)
```

### Chargement lazy du modèle d'embeddings

Le modèle `SentenceTransformer` (~90 MB) est chargé une seule fois au premier appel, puis conservé en mémoire globale :

```python
_model = None  # Module-level singleton

def _load_model(model_name: str):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    _model = SentenceTransformer(model_name)
    ...
```

### pgvector optionnel

Le fichier `sql/04_rag_tables.sql` est intentionnellement **sans pgvector** (compatible PostgreSQL pur). L'extension pgvector est dans un fichier séparé `04_rag_tables_pgvector.sql` et s'applique uniquement si pgvector est disponible. `RAG_BACKEND=jsonb` est le défaut stable.

### RAG non-bloquant

Tout le module RAG est enveloppé dans un try/except au niveau de `build_rag_context()`. Si le modèle d'embeddings ne se charge pas, si la base est inaccessible, ou si la recherche échoue → le service continue normalement avec `RAGContext(used=False)`.

---

## 20. Bugs corrigés et historique

| Bug | Symptôme | Cause | Correction |
|---|---|---|---|
| String refs React | `Cannot have string refs` sur `AIEntityInsightPanel` | Prop nommée `ref` passée à un composant fonctionnel | Renommée en `entityRef` |
| Structure JSX corrompue | Rendu vide sur `AIEntityInsightPanel` | Insertion du mode `inline` qui cassait les balises | Réécriture complète avec `PanelHeader`/`PanelBody` |
| `rag_chunks` manquante | Ingestion échoue avec `relation does not exist` | `CREATE EXTENSION IF NOT EXISTS vector` bloquait l'exécution si pgvector absent | SQL réécrit sans pgvector, extension dans fichier séparé |
| Syntaxe `:param::jsonb` | `syntax error at or near ":"` avec psycopg3 | SQLAlchemy + psycopg3 ne parse pas `:param::type` correctement | Remplacé par `CAST(:param AS type)` partout |
| `NOT IN :indices` SQLAlchemy | `ProgrammingError` sur `delete_old_chunks` | SQLAlchemy `text()` ne supporte pas le binding de liste | Placeholders dynamiques `:idx_0, :idx_1, ...` |
| `get_settings` inexistant | `ImportError` au démarrage | Config utilise `settings = Settings()` (singleton), pas une factory | Remplacé par `from app.config import settings as _settings` |
| `RAG_BACKEND=pgvector` par défaut | Ingestion échoue sur Windows sans pgvector | Valeur par défaut dans `.env` | Changé en `RAG_BACKEND=jsonb` |
| Complexité cognitive `ingest_all` | Warning SonarLint (score 20 > 15) | Logique imbriquée dans la boucle principale | Extrait en `_ingest_file()` et `_embed_chunks()` |

---

## 21. Commandes de déploiement

### Installation initiale

```powershell
# Créer et activer l'environnement virtuel
cd C:\Users\ataou\OneDrive\Desktop\lamalif-telegestion\smart-lighting-ai
python -m venv .venv
.\.venv\Scripts\activate

# Installer les dépendances
pip install fastapi uvicorn[standard] python-dotenv pydantic pydantic-settings
pip install sqlalchemy "psycopg[binary]" sqlglot httpx openai groq
pip install sentence-transformers numpy scikit-learn pgvector
```

### Créer les tables RAG

```powershell
psql -U postgres -d lampadaire -f .\sql\04_rag_tables.sql
```

Ou via le script :
```powershell
.\scripts\setup_rag_db.ps1
```

### Démarrer le service

```powershell
.\.venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

### Lancer l'ingestion RAG

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8090/rag/ingest" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"force_reingest":true}' | ConvertTo-Json -Depth 10
```

---

## 22. Tests API — commandes PowerShell

### Health check

```powershell
Invoke-RestMethod -Uri "http://localhost:8090/health" -Method GET
```

### Statut RAG

```powershell
Invoke-RestMethod -Uri "http://localhost:8090/rag/status" -Method GET | ConvertTo-Json -Depth 10
```

### Requête IA avec RAG

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8090/ai/query" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"question":"Quelle zone est la plus critique ?"}' | ConvertTo-Json -Depth 10
```

Vérifier dans la réponse : `rag.used = true`, `rag.chunks_count > 0`.

### Autres questions de test

```powershell
# Test règle métier (LCU avant lampadaires)
'{"question":"Pourquoi vérifier la LCU avant les lampadaires ?"}' | ...

# Test diagnostic équipement
'{"question":"Quels lampadaires ont une température driver élevée ?"}' | ...

# Test KPIs globaux
'{"question":"Donne-moi la situation globale du réseau."}' | ...
```

### Page Insights

```powershell
Invoke-RestMethod -Uri "http://localhost:8090/ai/page-insights/dashboard" -Method GET | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8090/ai/page-insights/lcus" -Method GET | ConvertTo-Json -Depth 10
```

### Entity Insights

```powershell
# Diagnostic lampadaire id=1
Invoke-RestMethod -Uri "http://localhost:8090/ai/entity-insights/lampadaire/1" -Method GET | ConvertTo-Json -Depth 10

# Forcer régénération (bypass cache)
Invoke-RestMethod -Uri "http://localhost:8090/ai/entity-insights/lcu/1?refresh=true" -Method GET | ConvertTo-Json -Depth 10
```

### Validation SQL manuelle

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8090/ai/sql-validate" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"sql":"SELECT zone, offline_count FROM ai_zone_health LIMIT 10"}' | ConvertTo-Json
```

---

*Généré le 2026-06-10 — Projet Lamalif Télégestion — Module IA v1.0*
