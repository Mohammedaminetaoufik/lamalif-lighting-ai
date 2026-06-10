# Dictionnaire des vues IA — Smart Lighting Télégestion

Ce fichier décrit toutes les vues PostgreSQL accessibles par l'assistant IA.
Ces vues sont en lecture seule et commencent toutes par `ai_`.

---

## Vue : ai_lampadaire_status

**Objectif :** État général de chaque lampadaire du réseau.

**Colonnes principales :**
- id, reference, zone, etat (online/offline/maintenance)
- intensite (0-100%), puissance (W), commissioning_status
- latitude, longitude, lcu_id, lcu_reference
- last_seen_at, type_driver, driver_brand, driver_model
- nominal_power_w, energy_kwh, operating_hours
- fault_status, location_status

**Quand utiliser :** Questions sur l'état des lampadaires, quels sont offline, intensités, LCU associée, historique de communication.

**Exemples de questions :** Quels lampadaires sont hors ligne ? Combien de lampadaires sont en maintenance ? Quel lampadaire consomme le plus ?

**Exemple SQL :**
```sql
SELECT reference, zone, etat, lcu_reference, last_seen_at
FROM ai_lampadaire_status
WHERE etat = 'offline'
ORDER BY last_seen_at ASC NULLS FIRST
LIMIT 100
```

---

## Vue : ai_lcu_status

**Objectif :** État des LCUs (passerelles) avec compteurs de lampadaires associés.

**Colonnes principales :**
- id, reference, name, ip_address, port, zone, status
- lampadaires_count, online_count, offline_count, maintenance_count
- protocol, last_seen_at, last_sync_at, latitude, longitude

**Quand utiliser :** Questions sur les LCUs, quelle LCU concentre le plus de lampadaires hors ligne, statut réseau.

**Exemple SQL :**
```sql
SELECT reference, zone, offline_count, lampadaires_count, last_seen_at
FROM ai_lcu_status
ORDER BY offline_count DESC
LIMIT 10
```

---

## Vue : ai_open_alerts

**Objectif :** Alertes ouvertes avec contexte lampadaire et LCU.

**Colonnes principales :**
- id, severity (critical/warning/info), status, message, created_at
- lampadaire_id, lampadaire_reference, zone, lcu_reference
- type, probable_cause, recommended_action
- acknowledged_at, maintenance_related

**Quand utiliser :** Questions sur les alertes actives, alertes critiques, causes probables, actions recommandées.

**Exemple SQL :**
```sql
SELECT lampadaire_reference, zone, severity, message, created_at
FROM ai_open_alerts
WHERE severity = 'critical'
ORDER BY created_at DESC
LIMIT 100
```

---

## Vue : ai_workorders

**Objectif :** Bons de travail et interventions terrain.

**Colonnes principales :**
- id, title, status, priority, created_at
- lampadaire_id, lampadaire_reference, zone, lcu_reference
- description, probable_cause, recommended_action
- assigned_to_name, due_date, crew_type, repeat_count

**Quand utiliser :** Questions sur les interventions ouvertes, bons de travail en cours, techniciens assignés.

---

## Vue : ai_telemetry_latest

**Objectif :** Dernière télémétrie reçue par lampadaire.

**Colonnes principales :**
- lampadaire_id, lampadaire_reference, zone
- temperature (°C), luminosite (%), puissance (W)
- courant (A), tension (V), measured_at

**Quand utiliser :** Questions sur les mesures physiques récentes, température, consommation instantanée, lampadaires sans télémétrie.

**Exemple SQL :**
```sql
SELECT lampadaire_reference, zone, temperature, puissance, measured_at
FROM ai_telemetry_latest
WHERE measured_at < NOW() - INTERVAL '15 minutes'
ORDER BY measured_at ASC
LIMIT 100
```

---

## Vue : ai_commissioning_status

**Objectif :** Progression de la mise en service terrain par lampadaire.

**Colonnes principales :**
- id, reference, zone, commissioning_status, commissioning_step
- test_comm_status, test_dimming_status, test_metering_status
- commissioned_at, commissioning_notes, location_status
- latitude, longitude, lcu_reference

**Quand utiliser :** Questions sur l'avancement du commissioning, tests échoués, lampadaires non encore commissionnés.

**Exemple SQL :**
```sql
SELECT reference, zone, commissioning_status, test_comm_status, test_dimming_status
FROM ai_commissioning_status
WHERE commissioning_status <> 'commissioned'
LIMIT 100
```

---

## Vue : ai_zone_health

**Objectif :** Santé globale de chaque zone géographique du réseau.

**Colonnes principales :**
- zone, total_lampadaires, online_count, offline_count, maintenance_count
- open_alerts_count, critical_alerts_count, warning_alerts_count
- open_workorders_count, lcus_count
- avg_intensity, total_energy_kwh, avg_power_w

**Quand utiliser :** Questions sur les zones critiques, comparaison inter-zones, priorités par zone, zones avec le plus d'anomalies.

**Exemple SQL :**
```sql
SELECT zone, offline_count, critical_alerts_count, open_workorders_count, total_lampadaires
FROM ai_zone_health
ORDER BY offline_count DESC, critical_alerts_count DESC
LIMIT 10
```

---

## Vue : ai_energy_summary

**Objectif :** Consommation énergétique agrégée par zone.

**Colonnes principales :**
- zone, lampadaires_count, total_energy_kwh, avg_energy_kwh
- total_operating_hours, avg_operating_hours
- total_nominal_power_w, avg_measured_power_w, avg_intensity

**Quand utiliser :** Questions sur la consommation, efficacité énergétique, optimisation éclairage.

**Exemple SQL :**
```sql
SELECT zone, total_energy_kwh, lampadaires_count, avg_measured_power_w
FROM ai_energy_summary
ORDER BY total_energy_kwh DESC
LIMIT 10
```

---

## Vue : ai_lampadaire_diagnostics

**Objectif :** Diagnostic technique détaillé par lampadaire.

**Colonnes exactes (liste complète) :**
- `lampadaire_id` — identifiant interne
- `reference` — référence lisible du lampadaire
- `zone` — zone géographique
- `etat` — état : 'online', 'offline', 'maintenance', 'unknown'
- `fault_status` — code panne driver (NULL = pas de panne)
- `driver_brand` — marque du driver LED
- `driver_model` — modèle du driver LED
- `driver_temperature` — température interne driver (°C)
- `led_module_temperature` — température module LED (°C)
- `energy_kwh` — énergie cumulée (kWh)
- `operating_hours` — heures de fonctionnement
- `last_temperature` — dernière température télémétrie (°C)
- `last_power` — dernière puissance mesurée (W)
- `last_current` — dernier courant mesuré (mA)
- `last_voltage` — dernière tension mesurée (V)
- `last_luminosity` — dernier niveau luminosité (%)
- `last_measure_at` — horodatage de la dernière mesure télémétrie
- `open_alerts_count` — nombre d'alertes ouvertes
- `critical_alerts_count` — nombre d'alertes critiques ouvertes
- `lcu_reference` — référence du LCU associé

**ATTENTION — colonnes inexistantes dans cette vue :**
- `last_seen_at` N'EXISTE PAS ici — utiliser `last_measure_at`
- `status` N'EXISTE PAS ici — utiliser `etat`
- `health_score` N'EXISTE PAS ici — utiliser `ai_lampadaires_health`

**Quand utiliser :** Diagnostic technique approfondi, problèmes driver, températures anormales, alertes liées.

**Exemple SQL :**
```sql
SELECT reference, zone, etat, fault_status, driver_temperature,
       open_alerts_count, critical_alerts_count, last_measure_at
FROM ai_lampadaire_diagnostics
WHERE etat = 'offline'
   OR open_alerts_count > 0
   OR critical_alerts_count > 0
   OR driver_temperature > 70
ORDER BY critical_alerts_count DESC, open_alerts_count DESC, driver_temperature DESC NULLS LAST
LIMIT 100
```

---

## Vue : ai_lcu_health

**Objectif :** Diagnostic LCU avec score de santé calculé (0-100).

**Colonnes principales :**
- lcu_id, reference, name, zone, ip_address, port, protocol, status
- last_seen_at, last_sync_at
- lampadaires_count, offline_count, maintenance_count
- open_alerts_count, critical_alerts_count, health_score

**Quand utiliser :** Questions sur la santé des LCUs, health_score, LCUs prioritaires à vérifier.

**Exemple SQL :**
```sql
SELECT reference, zone, health_score, offline_count, critical_alerts_count, last_seen_at
FROM ai_lcu_health
ORDER BY health_score ASC, offline_count DESC
LIMIT 10
```

---

## Vue : ai_workorder_age

**Objectif :** Bons de travail avec ancienneté calculée en heures.

**Colonnes principales :**
- id, title, status, priority, age_hours
- zone, lampadaire_reference, lcu_reference, assigned_to_name
- created_at, accepted_at, started_at, resolved_at

**Quand utiliser :** Questions sur les bons de travail anciens, interventions bloquées, charge par technicien.

**Exemple SQL :**
```sql
SELECT id, title, status, priority, age_hours, zone, assigned_to_name
FROM ai_workorder_age
WHERE status IN ('created', 'assigned', 'accepted', 'in_progress')
ORDER BY age_hours DESC
LIMIT 100
```

---

## Vue : ai_alert_summary

**Objectif :** Résumé des alertes ouvertes agrégées par zone, LCU et sévérité.

**Colonnes principales :**
- zone, lcu_reference, severity, total_alerts, latest_alert_at

**Quand utiliser :** Vue d'ensemble des alertes, concentrations par zone ou LCU.

---

## Vue : ai_dimming_status

**Objectif :** Capacité de variation d'intensité (dimming) par lampadaire.

**Colonnes principales :**
- lampadaire_id, reference, zone
- dimming_enabled, dimming_protocol, d4i_compatible
- current_intensity, last_command_at, lcu_reference

**Quand utiliser :** Questions sur le dimming, compatibilité D4i/DALI, profils d'intensité.

---

## Vue : ai_driver_health

**Objectif :** État technique des drivers LED avec mesures physiques.

**Colonnes principales :**
- id, reference, zone, driver_brand, driver_model, driver_protocol, type_driver
- nominal_power_w, output_current_ma, output_voltage_v, power_factor
- surge_protection, driver_temperature, led_module_temperature
- fault_status, last_seen_at

**Quand utiliser :** Questions sur les drivers, températures élevées, défauts électriques, protection surtension.

**Exemple SQL :**
```sql
SELECT reference, zone, driver_brand, driver_temperature, fault_status
FROM ai_driver_health
WHERE driver_temperature > 70
ORDER BY driver_temperature DESC
LIMIT 100
```

---

## Vue : ai_controller_network_status

**Objectif :** État des contrôleurs embarqués et qualité du signal réseau terrain.

**Colonnes principales :**
- id, reference, zone, controller_uid, controller_type, controller_status
- controller_signal_quality (0-100), controller_firmware
- controller_last_seen_at, controller_embedded, lcu_reference

**Quand utiliser :** Questions sur la connectivité terrain, signal faible, contrôleurs hors ligne.

**Exemple SQL :**
```sql
SELECT reference, zone, controller_signal_quality, controller_status
FROM ai_controller_network_status
WHERE controller_signal_quality < 40
ORDER BY controller_signal_quality ASC
LIMIT 100
```

---

## Vue : ai_map_assets

**Objectif :** Vue cartographique unifiée lampadaires et LCUs avec coordonnées GPS.

**Colonnes principales :**
- asset_type (lampadaire/lcu), id, reference, zone, status
- latitude, longitude, lcu_reference, has_location

**Quand utiliser :** Questions sur la localisation GPS, équipements sans coordonnées, vue cartographique.

**Exemple SQL :**
```sql
SELECT asset_type, reference, zone, status, has_location
FROM ai_map_assets
WHERE has_location = false
LIMIT 100
```

---

## Vue : ai_recent_activity

**Objectif :** Activité récente du réseau sur les 7 derniers jours.

**Colonnes principales :**
- activity_type, title, status, reference, zone, created_at

**Quand utiliser :** Questions sur les événements récents, historique d'activité.

---

## Vue : ai_maintenance_overview

**Objectif :** Vue maintenance globale par zone.

**Colonnes principales :**
- zone, total_lampadaires, maintenance_count
- open_workorders, resolved_workorders, open_alerts, critical_alerts

**Quand utiliser :** Vue d'ensemble maintenance, zones avec le plus d'interventions.

---

## Vue : ai_global_kpis

**Objectif :** KPIs globaux de la plateforme — une seule ligne de synthèse.

**Colonnes principales :**
- total_lampadaires, total_lcus
- offline_lampadaires, online_lampadaires, maintenance_lampadaires
- open_alerts, critical_alerts, open_workorders, total_energy_kwh

**Quand utiliser :** Questions globales sur le réseau, situation générale, tableau de bord.

**Exemple SQL :**
```sql
SELECT * FROM ai_global_kpis LIMIT 1
```

---

## Vue : ai_technician_workload

**Objectif :** Charge de travail par technicien.

**Colonnes principales :**
- technician_name, assigned_count, open_count, in_progress_count, resolved_count

**Quand utiliser :** Questions sur la disponibilité des techniciens, répartition des interventions.
