# Règles d'Analyse par Page — Smart Lighting Télégestion

Ce fichier définit les règles pour les analyses automatiques générées par l'IA sur chaque page admin.

---

## Page : Dashboard

**Objectif :** Vue synthétique de l'état global du réseau.

**Vues à utiliser :**
- `ai_global_kpis` — Indicateurs globaux (1 ligne)
- `ai_zone_health` — État par zone, zones critiques
- `ai_lcu_health` — LCUs prioritaires, health scores
- `ai_workorder_age` — Bons de travail les plus anciens

**Points d'analyse clés :**
- Taux d'équipements offline (offline_lampadaires / total_lampadaires)
- Nombre total d'alertes critiques
- Zones avec le plus de problèmes
- LCUs avec health_score < 50
- Bons de travail en retard (age_hours > 72)

**Résumé attendu :** Synthèse en 1-2 phrases sur l'état général du réseau.
**Analyse attendue :** Identification des zones critiques et des actions prioritaires.
**Recommandations attendues :** 2-4 actions opérationnelles concrètes.

---

## Page : Lampadaires

**Objectif :** Vue détaillée de l'état de tous les lampadaires.

**Vues à utiliser :**
- `ai_lampadaire_status` — État général, intensités, LCU associée
- `ai_lampadaire_diagnostics` — Problèmes techniques, températures, alertes

**Points d'analyse clés :**
- Taux de lampadaires offline par zone
- Concentration de pannes sur une même LCU
- Lampadaires avec temperature driver > 70°C
- Lampadaires sans télémétrie récente
- Fault_status non nuls

**Résumé :** Combien sont offline, en maintenance, en alerte.
**Recommandations :** Vérification LCUs prioritaires, interventions thermiques, maintenance préventive.

---

## Page : LCUs

**Objectif :** État des passerelles de contrôle.

**Vues à utiliser :**
- `ai_lcu_status` — Statut, compteurs lampadaires
- `ai_lcu_health` — Health scores, alertes

**Points d'analyse clés :**
- LCUs offline (status = 'offline')
- LCUs avec health_score < 50
- LCUs avec offline_count > 3
- LCUs sans synchronisation récente (last_sync_at ancien)

**Recommandations :** Intervention terrain sur LCUs critiques, vérification réseau.

---

## Page : Alertes

**Objectif :** Gestion des alertes du réseau.

**Vues à utiliser :**
- `ai_alert_summary` — Résumé par zone/LCU/sévérité
- `ai_open_alerts` — Alertes ouvertes détaillées

**Points d'analyse clés :**
- Nombre total d'alertes critiques
- Zones avec concentration d'alertes
- LCUs avec multiple alertes
- Alertes sans bon de travail associé (work_order_id null)
- Alertes les plus anciennes

**Recommandations :** Priorisation des alertes critiques, création de bons de travail, intervention groupée par zone.

---

## Page : Bons de Travail (WorkOrders)

**Objectif :** Suivi des interventions terrain.

**Vues à utiliser :**
- `ai_workorder_age` — Ancienneté des bons, techniciens
- `ai_workorders` — Détail des bons ouverts

**Points d'analyse clés :**
- Bons de travail ouverts depuis > 48h
- Bons de travail critiques non assignés
- Techniciens avec charge de travail élevée
- Bons en retard par rapport à la due_date

**Recommandations :** Escalade des bons en retard, réassignation, planification des interventions.

---

## Page : Énergie

**Objectif :** Analyse de la consommation énergétique.

**Vues à utiliser :**
- `ai_energy_summary` — Consommation par zone

**Points d'analyse clés :**
- Zones avec consommation anormalement élevée
- Écart entre puissance nominale et mesurée
- Zones avec avg_intensity élevée (potentiel d'optimisation)
- Zones avec consommation anormalement basse (équipements offline)

**Recommandations :** Analyse des profils de dimming, optimisation sous validation humaine.

---

## Page : Commissioning

**Objectif :** Suivi de la mise en service des nouveaux équipements.

**Vues à utiliser :**
- `ai_commissioning_status` — État du commissioning

**Points d'analyse clés :**
- Lampadaires bloqués en commissioning (non 'commissioned')
- Tests échoués (test_comm_status, test_dimming_status = 'failed')
- Lampadaires sans GPS mais en commissioning
- Lampadaires sans LCU associée

**Recommandations :** Correction des tests échoués, ajout GPS, association LCU.

---

## Page : Carte (Map)

**Objectif :** Vue cartographique des équipements.

**Vues à utiliser :**
- `ai_map_assets` — Assets avec coordonnées GPS

**Points d'analyse clés :**
- Équipements sans localisation GPS (has_location = false)
- Distribution géographique des pannes
- Zones géographiques sans couverture

**Recommandations :** Mise à jour des coordonnées GPS, analyse de couverture réseau.

---

## Règles générales d'analyse IA par page

1. **Baser sur les vraies données** — Le résumé et l'analyse doivent utiliser les chiffres réels des requêtes SQL.
2. **Ne pas inventer** — Si une métrique est absente, l'indiquer clairement.
3. **Priorité adaptée** — La priorité doit refléter la gravité réelle des données.
4. **Recommandations actionnables** — Chaque recommandation doit être concrète et applicable.
5. **Pas d'action automatique** — Ne jamais proposer d'action terrain sans validation humaine.
6. **Contexte métier** — Utiliser le vocabulaire Smart Lighting (LCU, health_score, commissioning, etc.).
