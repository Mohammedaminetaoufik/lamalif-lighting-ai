# Règles Métier — Smart Lighting Télégestion

Ce fichier décrit les règles métier du domaine de la télégestion d'éclairage public intelligent.

---

## 1. Définition d'une zone critique

Une zone est considérée critique si elle cumule plusieurs des conditions suivantes :
- Nombreux lampadaires offline (etat = 'offline')
- Plusieurs alertes de sévérité critique (severity = 'critical')
- Plusieurs bons de travail ouverts (status IN 'created', 'assigned', 'accepted', 'in_progress')
- Consommation anormale ou très élevée
- LCU(s) avec health_score faible

**Vue à utiliser :** `ai_zone_health`
**Tri recommandé :** ORDER BY offline_count DESC, critical_alerts_count DESC, open_workorders_count DESC

---

## 2. Définition d'une LCU critique

Une LCU doit être traitée en priorité si :
- Son statut est 'offline'
- Son health_score est inférieur à 50 (sur 100)
- Elle concentre plusieurs lampadaires offline (offline_count élevé)
- Elle a des alertes critiques liées (critical_alerts_count > 0)
- Sa dernière synchronisation est ancienne (last_sync_at > 30 minutes)
- Plusieurs lampadaires de cette LCU ont le même problème

**Règle clé :** Si plusieurs lampadaires liés à la même LCU sont offline, le problème est probablement centralisé au niveau LCU. Vérifier la LCU AVANT d'envoyer des techniciens sur chaque lampadaire.

**Vue à utiliser :** `ai_lcu_health` (colonne health_score)

---

## 3. Définition d'un lampadaire critique

Un lampadaire est prioritaire si :
- Son état est 'offline'
- Il a des alertes critiques ouvertes (critical_alerts_count > 0)
- Sa télémétrie est absente ou trop ancienne (last_measure_at)
- Sa température driver est élevée (driver_temperature > 70°C)
- Il a un work order critique ou en retard
- Son fault_status est non nul

**Vue à utiliser :** `ai_lampadaire_diagnostics`, `ai_lampadaire_status`

---

## 4. Règles de mise en service (commissioning)

Un lampadaire peut être validé comme 'commissioned' seulement si tous les critères sont réunis :
- test_comm_status = 'success' (communication validée)
- test_dimming_status = 'success' (variation d'intensité validée)
- test_metering_status = 'success' OU non applicable
- Localisation GPS présente (location_status = 'located', latitude et longitude non nulles)
- LCU associée correcte (lcu_reference non nul)
- Aucune alerte critique active

**Si un test échoue :** Le commissioning doit être bloqué jusqu'à correction.

**Vue à utiliser :** `ai_commissioning_status`

---

## 5. Règles de dimming

- Le dimming doit TOUJOURS être proposé comme recommandation, jamais appliqué automatiquement.
- Toute modification d'intensité doit être validée par un opérateur humain.
- Les profils de dimming doivent être basés sur des plages horaires et validés manuellement.
- Une optimisation de consommation via dimming nécessite une analyse terrain préalable.
- Ne jamais réduire l'intensité en dessous des seuils réglementaires de sécurité routière.

**Vue à utiliser :** `ai_dimming_status`

---

## 6. Priorisation des interventions maintenance

Critères de priorisation dans l'ordre décroissant :
1. Alertes critiques actives (severity = 'critical')
2. Ancienneté du bon de travail (age_hours élevé)
3. Nombre d'équipements impactés (un seul lampadaire vs une LCU avec 20 lampadaires)
4. Zone à forte densité de circulation
5. LCU associée (problème centralisé = priorité plus haute)
6. Nature du défaut (électrique > mécanique > logiciel)

**Vue à utiliser :** `ai_workorder_age`, `ai_open_alerts`

---

## 7. Règle LCU avant lampadaires

Avant de créer des interventions individuelles sur chaque lampadaire d'une zone :
1. Vérifier si les lampadaires offline partagent la même LCU
2. Si oui, diagnostiquer la LCU en premier
3. Une seule panne LCU peut mettre hors ligne 10 à 50 lampadaires
4. Économie d'interventions terrain : 1 intervention LCU au lieu de N interventions lampadaires

---

## 8. Règles énergétiques

- La consommation est mesurée en kWh par lampadaire et agrégée par zone
- Une consommation anormalement élevée peut indiquer : driver défaillant, profil de dimming non optimisé, lampadaires en mode forcé (100%)
- Une consommation anormalement faible peut indiquer : lampadaire offline, capteur défaillant
- Toute recommandation de réduction de consommation nécessite une validation humaine

**Vue à utiliser :** `ai_energy_summary`, `ai_zone_health`

---

## 9. Températures et alertes thermiques

- Température driver normale : < 60°C
- Température driver élevée : 60-70°C (surveiller)
- Température driver critique : > 70°C (intervention requise)
- Température LED module normale : < 80°C
- En cas de température critique : planifier inspection terrain immédiate

**Vue à utiliser :** `ai_driver_health`, `ai_lampadaire_diagnostics`

---

## 10. Santé réseau global

Le réseau est considéré :
- **Sain** : offline < 5%, alertes critiques < 2, work orders ouverts < 5% total
- **Dégradé** : offline 5-15%, alertes critiques modérées
- **Critique** : offline > 15% OU > 5 alertes critiques simultanées

**Vue à utiliser :** `ai_global_kpis`, `ai_zone_health`
