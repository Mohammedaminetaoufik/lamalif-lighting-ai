-- ============================================================
-- 05_ai_daily_operations_views.sql
-- Vues "opérations 24h" pour le daily digest IA.
-- Le service IA lit ces vues ai_* (jamais les tables brutes).
--   psql -U postgres -d lampadaire -f 05_ai_daily_operations_views.sql
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- ai_alerts_24h : activité alertes sur 24h (1 ligne)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_alerts_24h AS
SELECT
    COUNT(*)                                                 AS total_alerts_24h,
    COUNT(*) FILTER (WHERE severity = 'critical')           AS critical_alerts_24h,
    COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed')) AS open_alerts_24h
FROM alerts
WHERE created_at >= NOW() - INTERVAL '24 hours';

GRANT SELECT ON ai_alerts_24h TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- ai_workorders_24h : activité bons de travail sur 24h (1 ligne)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_workorders_24h AS
SELECT
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours')                                  AS new_workorders_24h,
    COUNT(*) FILTER (WHERE status IN ('resolved','closed') AND resolved_at >= NOW() - INTERVAL '24 hours') AS resolved_workorders_24h
FROM work_orders;

GRANT SELECT ON ai_workorders_24h TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- ai_daily_operations_kpis : KPIs globaux + deltas 24h (1 ligne)
-- Combine ai_global_kpis avec les vues 24h ci-dessus.
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_daily_operations_kpis AS
SELECT
    g.total_lampadaires,
    g.offline_lampadaires,
    g.online_lampadaires,
    g.maintenance_lampadaires,
    g.open_alerts,
    g.critical_alerts,
    g.open_workorders,
    g.total_energy_kwh,
    a.total_alerts_24h        AS new_alerts_24h,
    a.critical_alerts_24h,
    w.new_workorders_24h,
    w.resolved_workorders_24h
FROM ai_global_kpis g
CROSS JOIN ai_alerts_24h a
CROSS JOIN ai_workorders_24h w;

GRANT SELECT ON ai_daily_operations_kpis TO ai_readonly;

-- Fin du script
