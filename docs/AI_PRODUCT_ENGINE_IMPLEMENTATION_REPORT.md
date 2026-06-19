# Rapport d'implémentation — Moteur de recommandations & scores

Tranche : **moteur de règles + scores d'abord** (du plan 15 phases).

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `app/recommendations/__init__.py` | API publique du moteur |
| `app/recommendations/schemas.py` | `Recommendation` + enums + `make_recommendation` |
| `app/recommendations/utils.py` | helpers (`hours_since`, seuils, `num`…) |
| `app/recommendations/scoring.py` | 4 familles de scores 0–100 |
| `app/recommendations/rule_engine.py` | orchestrateur `evaluate_lampadaire/lcu/page/daily` |
| `app/recommendations/formatter.py` | tri, dédup, priorité globale, sérialisation |
| `app/recommendations/lampadaire_rules.py` | disponibilité lampadaire |
| `app/recommendations/lcu_rules.py` | LCU (entité + ligne) |
| `app/recommendations/zone_rules.py` | panne groupée par zone |
| `app/recommendations/driver_rules.py` | surchauffe driver |
| `app/recommendations/maintenance_rules.py` | WO en retard (entité + lignes) |
| `app/recommendations/commissioning_rules.py` | mise en service incomplète |
| `app/recommendations/energy_rules.py` | dimming inactif / conso |
| `app/recommendations/data_quality_rules.py` | GPS / LCU / zone / télémétrie manquants |
| `sql/05_ai_daily_operations_views.sql` | vues `ai_alerts_24h`, `ai_workorders_24h`, `ai_daily_operations_kpis` |
| `requirements-prod.txt` | dépendances prod minimales |
| `scripts/test_recommendation_engine.py` | 13 tests purs (sans DB ni LLM) |
| `docs/AI_PRODUCT_ENGINE.md` | doc produit |
| `docs/INSTALLATION_AI.md` | installation |

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `app/routes/entity_insights.py` | scores + recommandations rule-based (refresh=false ET true) ; champs `risk_score`, `maintainability_score`, `communication_health_score`, `recommendations`, `source`, `llm_available` |
| `app/routes/page_insights.py` | `rule_recommendations` rule-based (0 token) ; requête energy enrichie (avg_intensity, nominal/measured power) ; `source`, `llm_available` |
| `app/routes/daily_digest.py` | KPIs via `ai_daily_operations_kpis` (fallback inclus) ; `rule_based_recommendations` ; cooldown 429 propre ; `llm_available`, `retry_after_seconds` |

## Règles ajoutées
Disponibilité (offline / offline+alerte / offline+LCU offline), LCU (offline, health<30/60, ratio offline>30%),
zone (ratio offline ≥0.8/0.4/>0), driver (≥80/≥70 °C), maintenance (WO>48h, critique>24h),
commissioning (statut + tests échoués), énergie (dimming inactif), data quality (GPS/LCU/zone/télémétrie).

## Scores ajoutés
`risk_score`, `maintainability_score`, `communication_health_score` (lampadaire/LCU),
`lcu_risk_score`, `zone_risk_score`, `energy_efficiency_score`.

## Tests réalisés
- `scripts/test_recommendation_engine.py` : **13/13 PASS** (zones, LCU, lampadaire offline/critique,
  driver chaud, WO>48h, maintainability GPS/LCU, daily & page sans LLM).
- `python -c "from app.main import app"` : **OK** (19 routes).

## Tests NON réalisés (nécessitent services lancés)
- Appels HTTP live (`GET /ai/daily-digest`, `/ai/entity-insights/...`) — à lancer une fois Postgres + uvicorn démarrés.
- Application réelle de `sql/05_ai_daily_operations_views.sql` (le code a un fallback si la vue n'existe pas encore).

## Risques restants
- Le frontend n'affiche pas encore `rule_recommendations` / scores (tranche suivante : `RecommendationCard`, `ScoreBadge`).
- `ai_daily_operations_kpis` doit être appliquée pour lire les vues 24h ; sinon fallback automatique sur les requêtes inline.
- Cache moteur en mémoire (perdu au redémarrage) — comportement voulu.

## Prochaines étapes
1. Affichage frontend des recommandations structurées + badges de score.
2. RAG benchmarks (Phase 11) si les fichiers Excel sont fournis.
3. Décision RAG_BACKEND jsonb vs pgvector.
