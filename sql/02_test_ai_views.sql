-- ============================================================
-- 02_test_ai_views.sql
-- Tests de validation — exécuter en tant que ai_readonly
-- psql -U ai_readonly -d lampadaire -f 02_test_ai_views.sql
-- ============================================================

SELECT 'ai_lampadaire_status'        AS view_name, COUNT(*) AS rows FROM ai_lampadaire_status;
SELECT 'ai_lcu_status'               AS view_name, COUNT(*) AS rows FROM ai_lcu_status;
SELECT 'ai_open_alerts'              AS view_name, COUNT(*) AS rows FROM ai_open_alerts;
SELECT 'ai_workorders'               AS view_name, COUNT(*) AS rows FROM ai_workorders;
SELECT 'ai_telemetry_latest'         AS view_name, COUNT(*) AS rows FROM ai_telemetry_latest;
SELECT 'ai_commissioning_status'     AS view_name, COUNT(*) AS rows FROM ai_commissioning_status;
SELECT 'ai_zone_health'              AS view_name, COUNT(*) AS rows FROM ai_zone_health;
SELECT 'ai_energy_summary'           AS view_name, COUNT(*) AS rows FROM ai_energy_summary;
SELECT 'ai_lampadaire_diagnostics'   AS view_name, COUNT(*) AS rows FROM ai_lampadaire_diagnostics;
SELECT 'ai_lcu_health'               AS view_name, COUNT(*) AS rows FROM ai_lcu_health;
SELECT 'ai_workorder_age'            AS view_name, COUNT(*) AS rows FROM ai_workorder_age;
SELECT 'ai_alert_summary'            AS view_name, COUNT(*) AS rows FROM ai_alert_summary;
SELECT 'ai_dimming_status'           AS view_name, COUNT(*) AS rows FROM ai_dimming_status;
SELECT 'ai_driver_health'            AS view_name, COUNT(*) AS rows FROM ai_driver_health;
SELECT 'ai_controller_network_status' AS view_name, COUNT(*) AS rows FROM ai_controller_network_status;
SELECT 'ai_map_assets'               AS view_name, COUNT(*) AS rows FROM ai_map_assets;
SELECT 'ai_recent_activity'          AS view_name, COUNT(*) AS rows FROM ai_recent_activity;
SELECT 'ai_maintenance_overview'     AS view_name, COUNT(*) AS rows FROM ai_maintenance_overview;
SELECT 'ai_global_kpis'              AS view_name, COUNT(*) AS rows FROM ai_global_kpis;
SELECT 'ai_technician_workload'      AS view_name, COUNT(*) AS rows FROM ai_technician_workload;

-- Spot checks
SELECT * FROM ai_global_kpis;
SELECT zone, total_lampadaires, offline_count, critical_alerts_count FROM ai_zone_health ORDER BY offline_count DESC LIMIT 5;
SELECT zone, total_energy_kwh FROM ai_energy_summary ORDER BY total_energy_kwh DESC LIMIT 5;
