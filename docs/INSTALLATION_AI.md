# Installation — Service IA Lamalif

## Dépendances

Deux fichiers existent :

| Fichier | Usage |
|---------|-------|
| **`requirements-prod.txt`** | **Production & dev propre** — liste minimale, vérifiée, déployable. |
| `requirements.txt` | Legacy — `pip freeze` d'un environnement global (180+ paquets : Django, TensorFlow, torch, opencv…). **Ne pas utiliser pour déployer.** |

## Installation propre (recommandée)

```bash
python -m venv venv
venv/Scripts/pip install -r requirements-prod.txt   # Windows
# source venv/bin/activate && pip install -r requirements-prod.txt  # Linux/Mac
```

## Configuration

Copier `.env.example` → `.env` et renseigner `DATABASE_URL`, `GROQ_API_KEY` (optionnel), etc.
Le moteur de recommandations **fonctionne sans clé LLM** ; Groq n'est utilisé que pour enrichir la narration (`refresh=true`).

## Base de données

Appliquer les vues IA (en tant que superuser PostgreSQL) :

```bash
psql -U postgres -d lampadaire -f sql/01_ai_views_extended.sql
psql -U postgres -d lampadaire -f sql/05_ai_daily_operations_views.sql
```

## Démarrage

```bash
venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

## Vérification

```bash
venv/Scripts/python.exe -c "from app.main import app"      # import OK
venv/Scripts/python.exe scripts/test_recommendation_engine.py  # tests moteur
```
