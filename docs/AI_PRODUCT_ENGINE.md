# Moteur décisionnel IA — Lamalif Télégestion

## Vision

Le service IA n'est pas un chatbot : c'est un **moteur décisionnel industriel** pour la
télégestion d'éclairage public. Il analyse l'état réseau, calcule des scores, priorise
les problèmes et recommande des actions terrain — de façon **déterministe et explicable**.

## Principe fondateur

> **Le code calcule. Le RAG explique. Le LLM reformule. Aucun ne décide à la place des règles.**

- **PostgreSQL (vues `ai_*`)** = source de vérité unique.
- **Moteur de règles** (`app/recommendations/`) = calcule priorités, scores, recommandations.
- **RAG** = contextualise avec la connaissance métier (specs drivers, protocoles…), n'invente jamais les chiffres.
- **LLM (Groq/OpenAI)** = optionnel, reformule la narration. Jamais d'écriture, jamais de décision critique.

## Architecture

```
PostgreSQL / vues ai_*
        ↓
Rule Engine (app/recommendations/)  ──→  Scores industriels
        ↓
RAG métier (contexte)
        ↓
LLM optionnel (refresh=true)  →  narration enrichie
        ↓
API IA structurée  →  Frontend web + app technicien
```

## Pourquoi Groq est optionnel

- Coût (tokens) et limites de débit (429).
- Fiabilité : une recommandation critique ne doit pas dépendre d'une hallucination LLM.
- **Conséquence** : tous les endpoints renvoient scores + recommandations **rule-based sans aucun token**.
  `refresh=true` ajoute seulement une narration LLM par-dessus.

## Recommandations structurées

Chaque `Recommendation` (`app/recommendations/schemas.py`) est explicable :

| Champ | Rôle |
|-------|------|
| `title` | Titre court |
| `reason` | Pourquoi (le raisonnement métier) |
| `action` | Quoi faire concrètement |
| `priority` | critical / high / medium / low |
| `category` | availability, communication, driver, maintenance, energy, commissioning, data_quality… |
| `evidence` | **Les chiffres réels utilisés** (offline_count, driver_temperature, age_hours…) |
| `source` | rule_based / rag_guided / llm_enriched / fallback |
| `confidence` | 0–1 |

## Scores industriels (0–100, `app/recommendations/scoring.py`)

| Score | Sens | Données |
|-------|------|---------|
| `risk_score` | Risque opérationnel (haut = urgent) | offline, alertes critiques, LCU offline, WO en retard, driver chaud, télémétrie absente, commissioning incomplet |
| `maintainability_score` | Facilité de maintenance (haut = bon) | GPS, LCU associée, télémétrie récente, WO, zone, commissioning |
| `communication_health_score` | Santé communication | last_seen, LCU offline, signal contrôleur |
| `energy_efficiency_score` | Efficacité énergétique (zone) | intensité/dimming, puissance vs nominal |

## Vues `ai_*` utilisées

`ai_lampadaire_status`, `ai_lampadaire_diagnostics`, `ai_lcu_status`, `ai_lcu_health`,
`ai_zone_health`, `ai_energy_summary`, `ai_workorder_age`, `ai_commissioning_status`,
`ai_open_alerts`, `ai_global_kpis`, et les vues 24h `ai_alerts_24h` / `ai_workorders_24h` /
`ai_daily_operations_kpis` (fichier `sql/05_ai_daily_operations_views.sql`).

## Endpoints

| Endpoint | Sans `refresh` (0 token) | Avec `refresh=true` |
|----------|--------------------------|---------------------|
| `GET /ai/daily-digest` | KPIs + `rule_based_recommendations` | + narration LLM (cooldown 5 min si 429) |
| `GET /ai/page-insights/{page}` | `rule_recommendations` + KPIs | + narration LLM |
| `GET /ai/entity-insights/{type}/{id}` | scores + `recommendations` + détails techniques | + diagnostic LLM |
| `GET /ai/suggestions` | questions dynamiques (SQL pur) | — |
| `POST /ai/query` | question libre → SQLGuard → SQL → LLM | (LLM attendu, question utilisateur) |

## Sécurité

- **SQLGuard** (`app/sql_guard.py`) intact — SELECT uniquement sur vues `ai_*`.
- Aucune écriture LLM (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE interdits).
- Pas de secrets dans le RAG ni les réponses.

## Limites du LLM

- Peut être indisponible (429) → l'UI ne doit jamais afficher « Groq error » comme panne grave,
  mais : « Analyse avancée temporairement indisponible. Les recommandations opérationnelles restent disponibles. »
- Ne calcule jamais un score ni une priorité critique.

## Roadmap ML (futur)

- Maintenance prédictive (modèle sur `street_light_fault_prediction_dataset`).
- Benchmarks LED/drivers/IoT ingérés dans le RAG (Phase 11).
- Affichage frontend `RecommendationCard` / `ScoreBadge` (tranche suivante).
