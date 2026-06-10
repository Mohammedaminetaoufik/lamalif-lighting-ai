# Exemples SQL — Smart Lighting Télégestion

Ce fichier contient des exemples de questions en français et les requêtes SQL correspondantes.
Ces exemples guident le LLM dans le choix de la bonne vue et la bonne structure SQL.

---

## Situation globale

**Question :** Donne-moi la situation globale du réseau.
```sql
SELECT * FROM ai_global_kpis LIMIT 1
```

**Question :** Combien de lampadaires sont en ligne, hors ligne et en maintenance ?
```sql
SELECT online_lampadaires, offline_lampadaires, maintenance_lampadaires, total_lampadaires
FROM ai_global_kpis LIMIT 1
```

---

## Zones

**Question :** Quelle zone est la plus critique ?
```sql
SELECT zone, offline_count, critical_alerts_count, open_workorders_count, total_lampadaires
FROM ai_zone_health
ORDER BY offline_count DESC, critical_alerts_count DESC, open_workorders_count DESC
LIMIT 10
```

**Question :** Quelles zones ont des alertes critiques ?
```sql
SELECT zone, critical_alerts_count, open_alerts_count, offline_count
FROM ai_zone_health
WHERE critical_alerts_count > 0
ORDER BY critical_alerts_count DESC
LIMIT 20
```

**Question :** Quelle zone consomme le plus d'énergie ?
```sql
SELECT zone, total_energy_kwh, lampadaires_count, avg_measured_power_w
FROM ai_energy_summary
ORDER BY total_energy_kwh DESC
LIMIT 10
```

**Question :** Donne-moi les priorités opérationnelles du jour.
```sql
SELECT zone, offline_count, critical_alerts_count, open_workorders_count
FROM ai_zone_health
WHERE offline_count > 0 OR critical_alerts_count > 0
ORDER BY critical_alerts_count DESC, offline_count DESC
LIMIT 10
```

---

## Lampadaires

**Question :** Quels lampadaires sont hors ligne ?
```sql
SELECT reference, zone, lcu_reference, last_seen_at
FROM ai_lampadaire_status
WHERE etat = 'offline'
ORDER BY last_seen_at ASC NULLS FIRST
LIMIT 100
```

**Question :** Quels lampadaires sont hors ligne dans une zone spécifique ?
```sql
SELECT reference, zone, lcu_reference, last_seen_at
FROM ai_lampadaire_status
WHERE etat = 'offline' AND zone ILIKE '%marrakech%'
LIMIT 100
```

**Question :** Quels lampadaires ont des alertes critiques ?
```sql
SELECT lampadaire_reference, zone, severity, message, created_at
FROM ai_open_alerts
WHERE severity = 'critical'
ORDER BY created_at DESC
LIMIT 100
```

**Question :** Quels lampadaires ont un problème technique (fault) ?
```sql
SELECT reference, zone, fault_status, driver_temperature, open_alerts_count
FROM ai_lampadaire_diagnostics
WHERE fault_status IS NOT NULL
ORDER BY critical_alerts_count DESC
LIMIT 100
```

**Question :** Quels lampadaires sont hors ligne, ont des alertes ou une température anormale ?
```sql
-- NOTE : colonne date = last_measure_at (PAS last_seen_at qui n'existe pas dans cette vue)
SELECT reference, zone, etat, fault_status,
       open_alerts_count, critical_alerts_count,
       driver_temperature, last_measure_at
FROM ai_lampadaire_diagnostics
WHERE etat = 'offline'
   OR open_alerts_count > 0
   OR critical_alerts_count > 0
   OR driver_temperature > 70
ORDER BY critical_alerts_count DESC, open_alerts_count DESC, driver_temperature DESC NULLS LAST
LIMIT 100
```

**Question :** Quels lampadaires n'ont pas envoyé de télémétrie récemment ?
```sql
SELECT lampadaire_reference, zone, measured_at
FROM ai_telemetry_latest
WHERE measured_at < NOW() - INTERVAL '15 minutes'
ORDER BY measured_at ASC NULLS FIRST
LIMIT 100
```

---

## LCUs

**Question :** Quelle LCU a le plus de lampadaires hors ligne ?
```sql
SELECT reference, zone, offline_count, lampadaires_count, last_seen_at
FROM ai_lcu_status
ORDER BY offline_count DESC
LIMIT 10
```

**Question :** Quelle LCU doit être vérifiée en priorité ?
```sql
SELECT reference, name, zone, health_score, offline_count, critical_alerts_count, last_seen_at
FROM ai_lcu_health
ORDER BY health_score ASC, offline_count DESC
LIMIT 10
```

**Question :** Quelles LCUs sont hors ligne ?
```sql
SELECT reference, zone, status, last_seen_at, last_sync_at
FROM ai_lcu_status
WHERE status = 'offline'
ORDER BY last_seen_at ASC NULLS FIRST
LIMIT 50
```

---

## Alertes

**Question :** Quelles sont les alertes critiques ouvertes ?
```sql
SELECT lampadaire_reference, zone, severity, message, type, created_at
FROM ai_open_alerts
WHERE severity = 'critical'
ORDER BY created_at DESC
LIMIT 100
```

**Question :** Quelle zone a le plus d'alertes critiques ?
```sql
SELECT zone, severity, total_alerts, latest_alert_at
FROM ai_alert_summary
WHERE severity = 'critical'
ORDER BY total_alerts DESC
LIMIT 20
```

---

## Bons de travail

**Question :** Quels bons de travail sont ouverts ?
```sql
SELECT id, title, priority, status, lampadaire_reference, zone, created_at
FROM ai_workorders
WHERE status IN ('created', 'assigned', 'accepted', 'in_progress')
ORDER BY created_at DESC
LIMIT 100
```

**Question :** Quels bons de travail sont ouverts depuis longtemps ?
```sql
SELECT id, title, status, priority, zone, age_hours, assigned_to_name
FROM ai_workorder_age
WHERE status IN ('created', 'assigned', 'accepted', 'in_progress')
ORDER BY age_hours DESC
LIMIT 100
```

---

## Commissioning

**Question :** Quels lampadaires sont encore en mise en service ?
```sql
SELECT reference, zone, commissioning_status, commissioning_step,
       test_comm_status, test_dimming_status, test_metering_status
FROM ai_commissioning_status
WHERE commissioning_status <> 'commissioned'
LIMIT 100
```

**Question :** Quels tests de commissioning ont échoué ?
```sql
SELECT reference, zone, test_comm_status, test_dimming_status, test_metering_status
FROM ai_commissioning_status
WHERE test_comm_status = 'failed'
   OR test_dimming_status = 'failed'
   OR test_metering_status = 'failed'
LIMIT 100
```

---

## Drivers et contrôleurs

**Question :** Quels drivers ont une température élevée ?
```sql
SELECT reference, zone, driver_brand, driver_model, driver_temperature, led_module_temperature
FROM ai_driver_health
WHERE driver_temperature > 70
ORDER BY driver_temperature DESC
LIMIT 100
```

**Question :** Quels contrôleurs ont un signal faible ?
```sql
SELECT reference, zone, controller_uid, controller_signal_quality, controller_status
FROM ai_controller_network_status
WHERE controller_signal_quality < 40
ORDER BY controller_signal_quality ASC
LIMIT 100
```

---

## Cartographie et GPS

**Question :** Quels équipements n'ont pas de localisation GPS ?
```sql
SELECT asset_type, reference, zone, status
FROM ai_map_assets
WHERE has_location = false
LIMIT 100
```

---

## Dimming

**Question :** Quels lampadaires sont compatibles D4i ?
```sql
SELECT reference, zone, dimming_protocol, d4i_compatible, current_intensity
FROM ai_dimming_status
WHERE d4i_compatible = true
LIMIT 100
```

---

## Techniciens

**Question :** Quelle est la charge de travail des techniciens ?
```sql
SELECT technician_name, open_count, in_progress_count, assigned_count
FROM ai_technician_workload
ORDER BY open_count DESC
LIMIT 20
```

---

## Activité récente

**Question :** Quelles sont les dernières activités sur le réseau ?
```sql
SELECT activity_type, title, status, reference, zone, created_at
FROM ai_recent_activity
ORDER BY created_at DESC
LIMIT 50
```
