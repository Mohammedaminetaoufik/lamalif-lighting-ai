# Smart Lighting AI Service

Ce service FastAPI sera utilisé pour construire un assistant IA SQL-to-Text pour Lamalif Télégestion.

## Objectif futur

- Recevoir une question admin en français
- Générer une requête SQL PostgreSQL sécurisée
- Valider la requête avec SQLGuard
- Exécuter seulement SELECT avec un rôle read-only
- Retourner tableau, résumé, graphique et recommandation

## Démarrage (Windows PowerShell)

```powershell
cd C:\Users\ataou\OneDrive\Desktop\lamalif-telegestion\smart-lighting-ai

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env

uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

## Tester

```
http://localhost:8090/
http://localhost:8090/health
http://localhost:8090/docs
```

## Structure

```
smart-lighting-ai/
├── app/
│   ├── main.py               # Point d'entrée FastAPI
│   ├── config.py             # Settings via pydantic-settings
│   ├── db.py                 # Connexion PostgreSQL (TODO)
│   ├── schemas.py            # Modèles Pydantic
│   ├── sql_guard.py          # Validation SQL (TODO)
│   ├── llm_client.py         # Client LLM (TODO)
│   ├── prompt_builder.py     # Construction des prompts (TODO)
│   ├── recommendation_engine.py  # Recommandations (TODO)
│   └── routes/
│       ├── health.py         # GET /health
│       ├── ai_query.py       # POST /ai/query (TODO)
│       └── schema.py         # GET /ai/schema (TODO)
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── run.ps1
```
