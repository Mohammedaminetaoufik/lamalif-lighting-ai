# ============================================================
# setup_rag_db.ps1 — Création des tables RAG dans PostgreSQL
# Usage : .\scripts\setup_rag_db.ps1
# Ou avec paramètres : .\scripts\setup_rag_db.ps1 -User postgres -DB lampadaire
# ============================================================

# NOTE : $Host est une variable automatique réservée de PowerShell — on utilise $DbHost
param(
    [string]$User   = "postgres",
    [string]$DB     = "lampadaire",
    [string]$DbHost = "localhost",
    [string]$Port   = "5432"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SqlFile   = Join-Path $ScriptDir "..\sql\04_rag_tables.sql"

Write-Host ""
Write-Host "=== Setup RAG Tables ===" -ForegroundColor Cyan
Write-Host "Host : $DbHost`:$Port"
Write-Host "DB   : $DB"
Write-Host "User : $User"
Write-Host "File : $SqlFile"
Write-Host ""

if (-not (Test-Path $SqlFile)) {
    Write-Host "ERREUR : fichier SQL introuvable : $SqlFile" -ForegroundColor Red
    exit 1
}

# Appliquer le fichier SQL principal (version JSONB stable)
Write-Host "Applying 04_rag_tables.sql ..." -ForegroundColor Yellow
psql -h $DbHost -p $Port -U $User -d $DB -f $SqlFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR lors de l'execution du script SQL." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verification des tables..." -ForegroundColor Yellow

# Vérifier que les deux tables existent
$checkSQL = "SELECT table_name FROM information_schema.tables WHERE table_name IN ('rag_documents','rag_chunks') ORDER BY table_name;"
psql -h $DbHost -p $Port -U $User -d $DB -c $checkSQL

Write-Host ""
Write-Host "=== Setup termine ===" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines etapes :" -ForegroundColor Cyan
Write-Host "  1. Verifier que RAG_BACKEND=jsonb dans .env"
Write-Host "  2. Demarrer FastAPI :"
Write-Host "     python -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload"
Write-Host "  3. Lancer l'ingestion :"
Write-Host "     Invoke-RestMethod -Uri 'http://localhost:8090/rag/ingest' -Method POST -ContentType 'application/json' -Body '{""force_reingest"":true}'"
Write-Host "  4. Verifier le statut :"
Write-Host "     Invoke-RestMethod -Uri 'http://localhost:8090/rag/status' -Method GET"
Write-Host ""
