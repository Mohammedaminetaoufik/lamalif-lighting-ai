-- ============================================================
-- 01_ai_views_extended.sql
-- Vues IA métier pour Lamalif Télégestion
-- Exécuter en tant que postgres (superuser) :
--   psql -U postgres -d lampadaire -f 01_ai_views_extended.sql
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. ai_lampadaire_status  (remplace et enrichit l'existante)
--    État complet des lampadaires actifs
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_lampadaire_status AS
SELECT
    l.id,
    l.reference,
    l.zone,
    l.etat,
    l.intensite,
    l.puissance,
    l.commissioning_status,
    l.latitude,
    l.longitude,
    l.lcu_id,
    l.lcu_reference,
    l.last_seen_at,
    -- colonnes enrichies
    l.quartier,
    l.type_driver,
    l.protocole,
    l.driver_brand,
    l.driver_model,
    l.driver_protocol,
    l.nominal_power_w,
    l.energy_kwh,
    l.operating_hours,
    l.fault_status,
    l.location_status,
    l.created_at,
    l.updated_at
FROM lampadaires l
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_lampadaire_status TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 2. ai_lcu_status  (remplace et enrichit l'existante)
--    État des LCUs + compteurs lampadaires
--    NB : auth_token intentionnellement exclu
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_lcu_status AS
SELECT
    lc.id,
    lc.reference,
    lc.name,
    lc.ip_address,
    lc.port,
    lc.zone,
    lc.status,
    COUNT(l.id)                                              AS lampadaires_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'online')             AS online_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'offline')            AS offline_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'maintenance')        AS maintenance_count,
    -- colonnes enrichies
    lc.protocol,
    lc.last_seen_at,
    lc.last_sync_at,
    lc.latitude,
    lc.longitude
FROM lcus lc
LEFT JOIN lampadaires l ON l.lcu_id = lc.id AND l.archived_at IS NULL
GROUP BY lc.id, lc.reference, lc.name, lc.ip_address, lc.port, lc.zone,
         lc.status, lc.protocol, lc.last_seen_at, lc.last_sync_at,
         lc.latitude, lc.longitude;

GRANT SELECT ON ai_lcu_status TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 3. ai_open_alerts  (remplace et enrichit l'existante)
--    Alertes non résolues avec contexte lampadaire/LCU
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_open_alerts AS
SELECT
    a.id,
    a.severity,
    a.status,
    a.message,
    a.created_at,
    l.id            AS lampadaire_id,
    l.reference     AS lampadaire_reference,
    l.zone,
    l.lcu_reference,
    -- colonnes enrichies
    a.type,
    a.probable_cause,
    a.recommended_action,
    a.acknowledged_at,
    a.maintenance_related
FROM alerts a
LEFT JOIN lampadaires l ON l.id = a.lampadaire_id
WHERE a.status NOT IN ('resolved', 'closed');

GRANT SELECT ON ai_open_alerts TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 4. ai_workorders  (remplace et enrichit l'existante)
--    Bons de travail avec contexte complet
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_workorders AS
SELECT
    wo.id,
    wo.title,
    wo.status,
    wo.priority,
    wo.created_at,
    wo.accepted_at,
    wo.started_at,
    wo.resolved_at,
    wo.lampadaire_id,
    l.reference     AS lampadaire_reference,
    wo.zone,
    lc.reference    AS lcu_reference,
    -- colonnes enrichies
    wo.description,
    wo.probable_cause,
    wo.recommended_action,
    wo.assigned_to_name,
    wo.due_date,
    wo.closed_at,
    wo.crew_type,
    wo.repeat_count
FROM work_orders wo
LEFT JOIN lampadaires l  ON l.id  = wo.lampadaire_id
LEFT JOIN lcus lc        ON lc.id = wo.lcu_id;

GRANT SELECT ON ai_workorders TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 5. ai_telemetry_latest  (recréée proprement)
--    Dernière mesure capteur par lampadaire
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_telemetry_latest AS
SELECT DISTINCT ON (sm.lampadaire_id)
    sm.lampadaire_id,
    l.reference     AS lampadaire_reference,
    l.zone,
    sm.temperature,
    sm.luminosite,
    sm.puissance,
    sm.courant,
    sm.tension,
    sm.created_at   AS measured_at
FROM sensor_measurements sm
JOIN lampadaires l ON l.id = sm.lampadaire_id
ORDER BY sm.lampadaire_id, sm.created_at DESC;

GRANT SELECT ON ai_telemetry_latest TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 6. ai_commissioning_status  (nouvelle)
--    Suivi détaillé de la mise en service terrain
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_commissioning_status AS
SELECT
    l.id,
    l.reference,
    l.zone,
    l.quartier,
    l.commissioning_status,
    l.commissioning_step,
    l.commissioned_at,
    l.test_comm_status,
    l.test_dimming_status,
    l.test_metering_status,
    l.commissioning_notes,
    l.location_status,
    l.latitude,
    l.longitude,
    l.lcu_reference,
    l.last_seen_at
FROM lampadaires l
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_commissioning_status TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 7. ai_zone_health  (nouvelle)
--    Santé globale agrégée par zone
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_zone_health AS
SELECT
    l.zone,
    COUNT(l.id)                                                  AS total_lampadaires,
    COUNT(l.id) FILTER (WHERE l.etat = 'online')                 AS online_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'offline')                AS offline_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'maintenance')            AS maintenance_count,
    COUNT(l.id) FILTER (WHERE l.commissioning_status = 'discovered')   AS discovered_count,
    COUNT(l.id) FILTER (WHERE l.commissioning_status = 'commissioned') AS commissioned_count,
    COALESCE(MAX(al.open_alerts),    0)                          AS open_alerts_count,
    COALESCE(MAX(al.critical_alerts),0)                          AS critical_alerts_count,
    COALESCE(MAX(al.warning_alerts), 0)                          AS warning_alerts_count,
    COALESCE(MAX(wo.open_workorders),0)                          AS open_workorders_count,
    COUNT(DISTINCT l.lcu_id)                                     AS lcus_count,
    ROUND(AVG(l.intensite)::numeric,  1)                         AS avg_intensity,
    ROUND(COALESCE(SUM(l.energy_kwh), 0)::numeric, 2)            AS total_energy_kwh,
    ROUND(AVG(l.puissance)::numeric,  1)                         AS avg_power_w
FROM lampadaires l
LEFT JOIN (
    SELECT lm.zone,
           COUNT(*)                                               AS open_alerts,
           COUNT(*) FILTER (WHERE a.severity = 'critical')       AS critical_alerts,
           COUNT(*) FILTER (WHERE a.severity = 'warning')        AS warning_alerts
    FROM alerts a
    JOIN lampadaires lm ON lm.id = a.lampadaire_id
    WHERE a.status NOT IN ('resolved', 'closed')
    GROUP BY lm.zone
) al ON al.zone = l.zone
LEFT JOIN (
    SELECT zone, COUNT(*) AS open_workorders
    FROM work_orders
    WHERE status NOT IN ('resolved', 'closed', 'cancelled')
    GROUP BY zone
) wo ON wo.zone = l.zone
WHERE l.archived_at IS NULL
GROUP BY l.zone;

GRANT SELECT ON ai_zone_health TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 8. ai_energy_summary  (nouvelle)
--    Consommation énergétique par zone
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_energy_summary AS
SELECT
    l.zone,
    COUNT(l.id)                                                   AS lampadaires_count,
    ROUND(COALESCE(SUM(l.energy_kwh),      0)::numeric, 2)        AS total_energy_kwh,
    ROUND(COALESCE(AVG(l.energy_kwh),      0)::numeric, 2)        AS avg_energy_kwh,
    ROUND(COALESCE(SUM(l.operating_hours), 0)::numeric, 1)        AS total_operating_hours,
    ROUND(COALESCE(AVG(l.operating_hours), 0)::numeric, 1)        AS avg_operating_hours,
    COALESCE(SUM(l.nominal_power_w),       0)                     AS total_nominal_power_w,
    ROUND(COALESCE(AVG(
        CASE WHEN l.etat = 'online' THEN l.puissance END
    ), 0)::numeric, 1)                                            AS avg_measured_power_w,
    ROUND(COALESCE(AVG(
        CASE WHEN l.etat = 'online' THEN l.intensite END
    ), 0)::numeric, 1)                                            AS avg_intensity
FROM lampadaires l
WHERE l.archived_at IS NULL
GROUP BY l.zone;

GRANT SELECT ON ai_energy_summary TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 9. ai_lampadaire_diagnostics  (nouvelle)
--    Diagnostic technique complet par lampadaire
--    Combine lampadaires + dernière télémétrie + alertes
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_lampadaire_diagnostics AS
SELECT
    l.id            AS lampadaire_id,
    l.reference,
    l.zone,
    l.etat,
    l.fault_status,
    l.driver_brand,
    l.driver_model,
    l.driver_temperature,
    l.led_module_temperature,
    l.energy_kwh,
    l.operating_hours,
    t.temperature   AS last_temperature,
    t.puissance     AS last_power,
    t.courant       AS last_current,
    t.tension       AS last_voltage,
    t.luminosite    AS last_luminosity,
    t.measured_at   AS last_measure_at,
    COALESCE(al.open_count,    0) AS open_alerts_count,
    COALESCE(al.critical_count,0) AS critical_alerts_count,
    l.lcu_reference
FROM lampadaires l
LEFT JOIN ai_telemetry_latest t ON t.lampadaire_id = l.id
LEFT JOIN (
    SELECT lampadaire_id,
           COUNT(*)                                         AS open_count,
           COUNT(*) FILTER (WHERE severity = 'critical')   AS critical_count
    FROM alerts
    WHERE status NOT IN ('resolved', 'closed')
    GROUP BY lampadaire_id
) al ON al.lampadaire_id = l.id
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_lampadaire_diagnostics TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 10. ai_lcu_health  (nouvelle)
--     Diagnostic LCU avec score de santé calculé
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_lcu_health AS
SELECT
    lc.id           AS lcu_id,
    lc.reference,
    lc.name,
    lc.zone,
    lc.ip_address,
    lc.port,
    lc.protocol,
    lc.status,
    lc.last_seen_at,
    lc.last_sync_at,
    COUNT(l.id)                                             AS lampadaires_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'offline')           AS offline_count,
    COUNT(l.id) FILTER (WHERE l.etat = 'maintenance')       AS maintenance_count,
    COALESCE(MAX(al.open_alerts),    0)                     AS open_alerts_count,
    COALESCE(MAX(al.critical_alerts),0)                     AS critical_alerts_count,
    GREATEST(0,
        100
        - (COUNT(l.id) FILTER (WHERE l.etat = 'offline') * 3)::int
        - (COALESCE(MAX(al.critical_alerts), 0) * 10)::int
        - (CASE WHEN lc.status = 'offline'  THEN 40 ELSE 0 END)
        - (CASE WHEN lc.status = 'unknown'  THEN 20 ELSE 0 END)
    ) AS health_score
FROM lcus lc
LEFT JOIN lampadaires l ON l.lcu_id = lc.id AND l.archived_at IS NULL
LEFT JOIN (
    SELECT lm.lcu_id,
           COUNT(*)                                         AS open_alerts,
           COUNT(*) FILTER (WHERE a.severity = 'critical') AS critical_alerts
    FROM alerts a
    JOIN lampadaires lm ON lm.id = a.lampadaire_id
    WHERE a.status NOT IN ('resolved', 'closed')
    GROUP BY lm.lcu_id
) al ON al.lcu_id = lc.id
GROUP BY lc.id, lc.reference, lc.name, lc.zone, lc.ip_address, lc.port,
         lc.protocol, lc.status, lc.last_seen_at, lc.last_sync_at;

GRANT SELECT ON ai_lcu_health TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 11. ai_workorder_age  (nouvelle)
--     Bons de travail avec ancienneté calculée en heures
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_workorder_age AS
SELECT
    wo.id,
    wo.title,
    wo.status,
    wo.priority,
    wo.created_at,
    wo.accepted_at,
    wo.started_at,
    wo.resolved_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - wo.created_at)) / 3600, 1) AS age_hours,
    wo.zone,
    l.reference     AS lampadaire_reference,
    lc.reference    AS lcu_reference,
    wo.assigned_to_name
FROM work_orders wo
LEFT JOIN lampadaires l  ON l.id  = wo.lampadaire_id
LEFT JOIN lcus lc        ON lc.id = wo.lcu_id;

GRANT SELECT ON ai_workorder_age TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 12. ai_alert_summary  (nouvelle)
--     Résumé alertes ouvertes par zone / LCU / sévérité
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_alert_summary AS
SELECT
    COALESCE(l.zone, 'Inconnu') AS zone,
    lc.reference                AS lcu_reference,
    a.severity,
    COUNT(*)                    AS total_alerts,
    MAX(a.created_at)           AS latest_alert_at
FROM alerts a
LEFT JOIN lampadaires l ON l.id = a.lampadaire_id
LEFT JOIN lcus lc       ON lc.id = l.lcu_id
WHERE a.status NOT IN ('resolved', 'closed')
GROUP BY l.zone, lc.reference, a.severity;

GRANT SELECT ON ai_alert_summary TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 13. ai_dimming_status  (nouvelle)
--     Capacité de dimming et protocoles par lampadaire
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_dimming_status AS
SELECT
    l.id            AS lampadaire_id,
    l.reference,
    l.zone,
    l.dimming_enabled,
    l.dimming_protocol,
    l.d4i_compatible,
    l.intensite     AS current_intensity,
    l.last_command_at,
    l.lcu_reference
FROM lampadaires l
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_dimming_status TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 14. ai_driver_health  (nouvelle)
--     État technique des drivers LED
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_driver_health AS
SELECT
    l.id,
    l.reference,
    l.zone,
    l.driver_brand,
    l.driver_model,
    l.driver_protocol,
    l.type_driver,
    l.nominal_power_w,
    l.output_current_ma,
    l.output_voltage_v,
    l.power_factor,
    l.surge_protection,
    l.driver_temperature,
    l.led_module_temperature,
    l.fault_status,
    l.last_seen_at
FROM lampadaires l
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_driver_health TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 15. ai_controller_network_status  (nouvelle)
--     État des contrôleurs embarqués et communication terrain
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_controller_network_status AS
SELECT
    l.id,
    l.reference,
    l.zone,
    l.controller_uid,
    l.controller_type,
    l.controller_status,
    l.controller_signal_quality,
    l.controller_firmware,
    l.controller_last_seen_at,
    l.controller_embedded,
    l.lcu_reference
FROM lampadaires l
WHERE l.archived_at IS NULL;

GRANT SELECT ON ai_controller_network_status TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 16. ai_map_assets  (nouvelle)
--     Vue cartographique : lampadaires + LCUs
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_map_assets AS
SELECT
    'lampadaire'                                                 AS asset_type,
    l.id,
    l.reference,
    l.zone,
    l.etat                                                       AS status,
    l.latitude,
    l.longitude,
    l.lcu_reference,
    (l.latitude IS NOT NULL AND l.longitude IS NOT NULL)         AS has_location
FROM lampadaires l
WHERE l.archived_at IS NULL

UNION ALL

SELECT
    'lcu'                                                        AS asset_type,
    lc.id,
    lc.reference,
    lc.zone,
    lc.status,
    lc.latitude,
    lc.longitude,
    lc.reference                                                 AS lcu_reference,
    (lc.latitude IS NOT NULL AND lc.longitude IS NOT NULL)       AS has_location
FROM lcus lc;

GRANT SELECT ON ai_map_assets TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 17. ai_recent_activity  (nouvelle)
--     Activité récente (7 derniers jours) — WO + alertes
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_recent_activity AS
SELECT
    'work_order'                                    AS activity_type,
    wo.title,
    wo.status,
    COALESCE(l.reference, wo.equipment_reference)  AS reference,
    wo.zone,
    wo.created_at
FROM work_orders wo
LEFT JOIN lampadaires l ON l.id = wo.lampadaire_id
WHERE wo.created_at > NOW() - INTERVAL '7 days'

UNION ALL

SELECT
    'alert'                                         AS activity_type,
    a.message                                       AS title,
    a.status,
    l.reference,
    l.zone,
    a.created_at
FROM alerts a
LEFT JOIN lampadaires l ON l.id = a.lampadaire_id
WHERE a.created_at > NOW() - INTERVAL '7 days'

ORDER BY created_at DESC;

GRANT SELECT ON ai_recent_activity TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 18. ai_maintenance_overview  (nouvelle)
--     Vue maintenance globale par zone
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_maintenance_overview AS
SELECT
    l.zone,
    COUNT(l.id)                                                  AS total_lampadaires,
    COUNT(l.id) FILTER (WHERE l.etat = 'maintenance')            AS maintenance_count,
    COALESCE(MAX(wo.open_workorders),     0)                     AS open_workorders,
    COALESCE(MAX(wo.resolved_workorders), 0)                     AS resolved_workorders,
    COALESCE(MAX(al.open_alerts),         0)                     AS open_alerts,
    COALESCE(MAX(al.critical_alerts),     0)                     AS critical_alerts
FROM lampadaires l
LEFT JOIN (
    SELECT zone,
           COUNT(*) FILTER (WHERE status NOT IN ('resolved','closed','cancelled')) AS open_workorders,
           COUNT(*) FILTER (WHERE status IN ('resolved','closed'))                 AS resolved_workorders
    FROM work_orders
    GROUP BY zone
) wo ON wo.zone = l.zone
LEFT JOIN (
    SELECT lm.zone,
           COUNT(*)                                              AS open_alerts,
           COUNT(*) FILTER (WHERE a.severity = 'critical')      AS critical_alerts
    FROM alerts a
    JOIN lampadaires lm ON lm.id = a.lampadaire_id
    WHERE a.status NOT IN ('resolved', 'closed')
    GROUP BY lm.zone
) al ON al.zone = l.zone
WHERE l.archived_at IS NULL
GROUP BY l.zone;

GRANT SELECT ON ai_maintenance_overview TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 19. ai_global_kpis  (nouvelle)
--     KPIs globaux — 1 seule ligne, tous les indicateurs clés
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_global_kpis AS
SELECT
    (SELECT COUNT(*) FROM lampadaires WHERE archived_at IS NULL)                                   AS total_lampadaires,
    (SELECT COUNT(*) FROM lcus)                                                                    AS total_lcus,
    (SELECT COUNT(*) FROM lampadaires WHERE etat = 'offline'     AND archived_at IS NULL)          AS offline_lampadaires,
    (SELECT COUNT(*) FROM lampadaires WHERE etat = 'online'      AND archived_at IS NULL)          AS online_lampadaires,
    (SELECT COUNT(*) FROM lampadaires WHERE etat = 'maintenance' AND archived_at IS NULL)          AS maintenance_lampadaires,
    (SELECT COUNT(*) FROM alerts WHERE status NOT IN ('resolved','closed'))                        AS open_alerts,
    (SELECT COUNT(*) FROM alerts WHERE severity = 'critical' AND status NOT IN ('resolved','closed')) AS critical_alerts,
    (SELECT COUNT(*) FROM work_orders WHERE status NOT IN ('resolved','closed','cancelled'))       AS open_workorders,
    (SELECT ROUND(COALESCE(SUM(energy_kwh),0)::numeric,2) FROM lampadaires WHERE archived_at IS NULL) AS total_energy_kwh;

GRANT SELECT ON ai_global_kpis TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- 20. ai_technician_workload  (nouvelle)
--     Charge de travail par technicien (depuis work_orders)
--     NB : utilise assigned_to_name uniquement, pas users.password
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ai_technician_workload AS
SELECT
    wo.assigned_to_name                                                         AS technician_name,
    COUNT(*)                                                                    AS assigned_count,
    COUNT(*) FILTER (WHERE wo.status NOT IN ('resolved','closed','cancelled'))  AS open_count,
    COUNT(*) FILTER (WHERE wo.status = 'in_progress')                          AS in_progress_count,
    COUNT(*) FILTER (WHERE wo.status IN ('resolved','closed'))                  AS resolved_count
FROM work_orders wo
WHERE wo.assigned_to_name IS NOT NULL
GROUP BY wo.assigned_to_name;

GRANT SELECT ON ai_technician_workload TO ai_readonly;


-- ─────────────────────────────────────────────────────────────
-- GRANT global de sécurité pour toutes les vues ai_*
-- ─────────────────────────────────────────────────────────────
GRANT SELECT ON ai_lampadaire_status          TO ai_readonly;
GRANT SELECT ON ai_lcu_status                 TO ai_readonly;
GRANT SELECT ON ai_open_alerts                TO ai_readonly;
GRANT SELECT ON ai_workorders                 TO ai_readonly;
GRANT SELECT ON ai_telemetry_latest           TO ai_readonly;
GRANT SELECT ON ai_commissioning_status       TO ai_readonly;
GRANT SELECT ON ai_zone_health                TO ai_readonly;
GRANT SELECT ON ai_energy_summary             TO ai_readonly;
GRANT SELECT ON ai_lampadaire_diagnostics     TO ai_readonly;
GRANT SELECT ON ai_lcu_health                 TO ai_readonly;
GRANT SELECT ON ai_workorder_age              TO ai_readonly;
GRANT SELECT ON ai_alert_summary              TO ai_readonly;
GRANT SELECT ON ai_dimming_status             TO ai_readonly;
GRANT SELECT ON ai_driver_health              TO ai_readonly;
GRANT SELECT ON ai_controller_network_status  TO ai_readonly;
GRANT SELECT ON ai_map_assets                 TO ai_readonly;
GRANT SELECT ON ai_recent_activity            TO ai_readonly;
GRANT SELECT ON ai_maintenance_overview       TO ai_readonly;
GRANT SELECT ON ai_global_kpis                TO ai_readonly;
GRANT SELECT ON ai_technician_workload        TO ai_readonly;

-- Fin du script
