from app.config import settings

_SCHEMA = """
Vues autorisées et leurs colonnes :

1. ai_lampadaire_status — État général des lampadaires
   id, reference, zone, etat, intensite, puissance, commissioning_status,
   latitude, longitude, lcu_id, lcu_reference, last_seen_at,
   quartier, type_driver, protocole, driver_brand, driver_model, driver_protocol,
   nominal_power_w, energy_kwh, operating_hours, fault_status, location_status,
   created_at, updated_at

2. ai_lcu_status — État des LCUs et compteurs lampadaires
   id, reference, name, ip_address, port, zone, status,
   lampadaires_count, online_count, offline_count, maintenance_count,
   protocol, last_seen_at, last_sync_at, latitude, longitude

3. ai_open_alerts — Alertes ouvertes avec contexte lampadaire/LCU
   id, severity, status, message, created_at,
   lampadaire_id, lampadaire_reference, zone, lcu_reference,
   type, probable_cause, recommended_action, acknowledged_at, maintenance_related

4. ai_workorders — Bons de travail
   id, title, status, priority, created_at, accepted_at, started_at, resolved_at,
   lampadaire_id, lampadaire_reference, zone, lcu_reference,
   description, probable_cause, recommended_action, assigned_to_name,
   due_date, closed_at, crew_type, repeat_count

5. ai_telemetry_latest — Dernière télémétrie par lampadaire
   lampadaire_id, lampadaire_reference, zone,
   temperature, luminosite, puissance, courant, tension, measured_at

6. ai_commissioning_status — Mise en service terrain
   id, reference, zone, quartier, commissioning_status, commissioning_step,
   commissioned_at, test_comm_status, test_dimming_status, test_metering_status,
   commissioning_notes, location_status, latitude, longitude, lcu_reference, last_seen_at

7. ai_zone_health — Santé globale par zone (1 ligne par zone)
   zone, total_lampadaires, online_count, offline_count, maintenance_count,
   discovered_count, commissioned_count,
   open_alerts_count, critical_alerts_count, warning_alerts_count,
   open_workorders_count, lcus_count, avg_intensity, total_energy_kwh, avg_power_w

8. ai_energy_summary — Consommation énergétique par zone
   zone, lampadaires_count, total_energy_kwh, avg_energy_kwh,
   total_operating_hours, avg_operating_hours,
   total_nominal_power_w, avg_measured_power_w, avg_intensity

9. ai_lampadaire_diagnostics — Diagnostic technique par lampadaire
   lampadaire_id, reference, zone, etat, fault_status,
   driver_brand, driver_model, driver_temperature, led_module_temperature,
   energy_kwh, operating_hours,
   last_temperature, last_power, last_current, last_voltage, last_luminosity, last_measure_at,
   open_alerts_count, critical_alerts_count, lcu_reference

10. ai_lcu_health — Diagnostic LCU avec score de santé (0-100)
    lcu_id, reference, name, zone, ip_address, port, protocol, status,
    last_seen_at, last_sync_at, lampadaires_count, offline_count, maintenance_count,
    open_alerts_count, critical_alerts_count, health_score

11. ai_workorder_age — Bons de travail avec ancienneté en heures
    id, title, status, priority, created_at, accepted_at, started_at, resolved_at,
    age_hours, zone, lampadaire_reference, lcu_reference, assigned_to_name

12. ai_alert_summary — Résumé alertes ouvertes par zone/LCU/sévérité
    zone, lcu_reference, severity, total_alerts, latest_alert_at

13. ai_dimming_status — Capacité dimming par lampadaire
    lampadaire_id, reference, zone,
    dimming_enabled, dimming_protocol, d4i_compatible,
    current_intensity, last_command_at, lcu_reference

14. ai_driver_health — État technique des drivers LED
    id, reference, zone, driver_brand, driver_model, driver_protocol, type_driver,
    nominal_power_w, output_current_ma, output_voltage_v, power_factor,
    surge_protection, driver_temperature, led_module_temperature,
    fault_status, last_seen_at

15. ai_controller_network_status — Contrôleurs embarqués et signal terrain
    id, reference, zone, controller_uid, controller_type, controller_status,
    controller_signal_quality, controller_firmware,
    controller_last_seen_at, controller_embedded, lcu_reference

16. ai_map_assets — Vue cartographique (lampadaires + LCUs)
    asset_type, id, reference, zone, status,
    latitude, longitude, lcu_reference, has_location

17. ai_recent_activity — Activité récente (7 derniers jours)
    activity_type, title, status, reference, zone, created_at

18. ai_maintenance_overview — Vue maintenance globale par zone
    zone, total_lampadaires, maintenance_count,
    open_workorders, resolved_workorders, open_alerts, critical_alerts

19. ai_global_kpis — KPIs globaux de la plateforme (1 seule ligne)
    total_lampadaires, total_lcus, offline_lampadaires, online_lampadaires,
    maintenance_lampadaires, open_alerts, critical_alerts,
    open_workorders, total_energy_kwh

20. ai_technician_workload — Charge de travail par technicien
    technician_name, assigned_count, open_count, in_progress_count, resolved_count
"""

_EXAMPLES = """
Question : Quels lampadaires sont hors ligne ?
SQL :
SELECT reference, zone, lcu_reference, last_seen_at
FROM ai_lampadaire_status
WHERE etat = 'offline'
LIMIT 100

Question : Quels lampadaires sont hors ligne dans Rabat ?
SQL :
SELECT reference, zone, lcu_reference, last_seen_at
FROM ai_lampadaire_status
WHERE etat = 'offline' AND zone ILIKE '%rabat%'
LIMIT 100

Question : Quelle LCU a le plus de lampadaires hors ligne ?
SQL :
SELECT reference, zone, offline_count, lampadaires_count
FROM ai_lcu_status
ORDER BY offline_count DESC
LIMIT 10

Question : Quelles zones ont le plus d'alertes critiques ?
SQL :
SELECT zone, COUNT(*) AS total_alertes
FROM ai_open_alerts
WHERE severity = 'critical'
GROUP BY zone
ORDER BY total_alertes DESC
LIMIT 100

Question : Quels bons de travail sont ouverts ?
SQL :
SELECT id, title, priority, status, lampadaire_reference, zone, lcu_reference, created_at
FROM ai_workorders
WHERE status IN ('created', 'assigned', 'accepted', 'in_progress')
ORDER BY created_at DESC
LIMIT 100

Question : Quels lampadaires n'ont pas envoyé de télémétrie récemment ?
SQL :
SELECT lampadaire_reference, zone, measured_at
FROM ai_telemetry_latest
WHERE measured_at < NOW() - INTERVAL '15 minutes'
ORDER BY measured_at ASC
LIMIT 100

Question : Donne-moi la situation globale du réseau.
SQL :
SELECT * FROM ai_global_kpis LIMIT 1

Question : Quelle zone est la plus critique ?
SQL :
SELECT zone, offline_count, critical_alerts_count, open_workorders_count, total_lampadaires
FROM ai_zone_health
ORDER BY offline_count DESC, critical_alerts_count DESC, open_workorders_count DESC
LIMIT 10

Question : Quelle zone consomme le plus ?
SQL :
SELECT zone, total_energy_kwh, lampadaires_count, total_operating_hours
FROM ai_energy_summary
ORDER BY total_energy_kwh DESC
LIMIT 10

Question : Quels lampadaires sont encore en mise en service ?
SQL :
SELECT reference, zone, commissioning_status, commissioning_step,
       test_comm_status, test_dimming_status, test_metering_status
FROM ai_commissioning_status
WHERE commissioning_status <> 'commissioned'
LIMIT 100

Question : Quels tests de commissioning ont échoué ?
SQL :
SELECT reference, zone, test_comm_status, test_dimming_status, test_metering_status
FROM ai_commissioning_status
WHERE test_comm_status = 'failed'
   OR test_dimming_status = 'failed'
   OR test_metering_status = 'failed'
LIMIT 100

Question : Quels drivers ont une température élevée ?
SQL :
SELECT reference, zone, driver_brand, driver_model, driver_temperature, led_module_temperature
FROM ai_driver_health
WHERE driver_temperature > 70
ORDER BY driver_temperature DESC
LIMIT 100

Question : Quels contrôleurs ont un signal faible ?
SQL :
SELECT reference, zone, controller_uid, controller_signal_quality, controller_status
FROM ai_controller_network_status
WHERE controller_signal_quality < 40
ORDER BY controller_signal_quality ASC
LIMIT 100

Question : Quels lampadaires sont compatibles D4i ?
SQL :
SELECT reference, zone, dimming_protocol, d4i_compatible, current_intensity
FROM ai_dimming_status
WHERE d4i_compatible = true
LIMIT 100

Question : Quels bons de travail sont ouverts depuis longtemps ?
SQL :
SELECT id, title, status, priority, zone, age_hours, assigned_to_name
FROM ai_workorder_age
WHERE status IN ('created', 'assigned', 'accepted', 'in_progress')
ORDER BY age_hours DESC
LIMIT 100

Question : Quelle LCU doit être vérifiée en priorité ?
SQL :
SELECT reference, name, zone, status, health_score,
       offline_count, critical_alerts_count, last_seen_at
FROM ai_lcu_health
ORDER BY health_score ASC, offline_count DESC
LIMIT 10

Question : Quels équipements n'ont pas de localisation GPS ?
SQL :
SELECT asset_type, reference, zone, status
FROM ai_map_assets
WHERE has_location = false
LIMIT 100

Question : Quelles sont les dernières activités ?
SQL :
SELECT activity_type, title, status, reference, zone, created_at
FROM ai_recent_activity
ORDER BY created_at DESC
LIMIT 50

Question : Quelle zone a le plus d'alertes critiques ?
SQL :
SELECT zone, severity, total_alerts, latest_alert_at
FROM ai_alert_summary
WHERE severity = 'critical'
ORDER BY total_alerts DESC
LIMIT 20

Question : Quels lampadaires ont un problème technique ?
SQL :
SELECT reference, zone, etat, fault_status,
       driver_temperature, open_alerts_count, critical_alerts_count
FROM ai_lampadaire_diagnostics
WHERE fault_status IS NOT NULL
   OR open_alerts_count > 0
   OR driver_temperature > 70
ORDER BY critical_alerts_count DESC, open_alerts_count DESC
LIMIT 100

Question : Combien de lampadaires par LCU ?
SQL :
SELECT reference, zone, lampadaires_count, online_count, offline_count
FROM ai_lcu_status
ORDER BY lampadaires_count DESC
LIMIT 20

Question : Donne-moi les priorités opérationnelles du jour.
SQL :
SELECT zone, offline_count, critical_alerts_count, open_workorders_count
FROM ai_zone_health
WHERE offline_count > 0 OR critical_alerts_count > 0
ORDER BY critical_alerts_count DESC, offline_count DESC
LIMIT 10

Question : Quelle est la charge des techniciens ?
SQL :
SELECT technician_name, open_count, in_progress_count, assigned_count
FROM ai_technician_workload
ORDER BY open_count DESC
LIMIT 20
"""


def build_sql_prompt(question: str, rag_context: str = "") -> str:
    allowed = ", ".join(settings.allowed_views_list)
    rag_section = rag_context if rag_context else ""
    return f"""Tu es un assistant SQL expert pour un système de gestion d'éclairage public intelligent (Smart Lighting).

RÈGLES ABSOLUES — tu dois les respecter sans exception :
- Génère UNIQUEMENT une requête SELECT PostgreSQL.
- Utilise UNIQUEMENT les vues autorisées : {allowed}
- N'utilise JAMAIS les tables brutes : lampadaires, lcus, alerts, users, work_orders, sensor_measurements, ou toute autre table.
- N'utilise JAMAIS les mots-clés : INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, GRANT, REVOKE.
- N'accède JAMAIS aux colonnes : password_hash, auth_token, secrets, ou toute donnée sensible.
- Ajoute toujours LIMIT si la question ne précise pas de limite.
- N'invente JAMAIS une table ou une colonne absente du schéma ci-dessous.
- Retourne UNIQUEMENT le SQL brut, sans markdown, sans ```sql, sans explication, sans commentaire.
- Pour les questions globales ("situation du réseau", "KPIs"), utilise ai_global_kpis.
- Pour les questions par zone, utilise ai_zone_health ou ai_energy_summary.
- Pour les questions de diagnostic technique, utilise ai_lampadaire_diagnostics ou ai_driver_health.
- Pour les questions de commissioning/mise en service, utilise ai_commissioning_status.
- Pour les questions sur le dimming, utilise ai_dimming_status.
- Pour les questions de score de santé LCU, utilise ai_lcu_health (colonne health_score).
- Pour les questions sur les bons de travail anciens, utilise ai_workorder_age (colonne age_hours).
- Pour les questions sur les controllers/signal, utilise ai_controller_network_status.

{_SCHEMA}

Exemples :
{_EXAMPLES}
{rag_section}
Question : {question}
SQL :"""
