-- ============================================================
-- 00_inspect_schema.sql
-- Inspection du schéma PostgreSQL public — base lampadaire
-- Exécuter en tant que postgres ou ai_readonly
-- ============================================================

SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
