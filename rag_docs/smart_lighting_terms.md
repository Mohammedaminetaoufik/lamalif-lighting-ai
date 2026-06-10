# Vocabulaire Smart Lighting — Télégestion Éclairage Public

Ce fichier définit les termes techniques utilisés dans la plateforme Lamalif Télégestion.

---

## Équipements

**Lampadaire**
Point lumineux géré individuellement par le système de télégestion. Chaque lampadaire possède un identifiant unique (reference), une localisation GPS, un driver LED, et est rattaché à une LCU. États possibles : online, offline, maintenance.

**LCU (Lighting Control Unit)**
Contrôleur ou passerelle locale permettant de superviser et commander un groupe de lampadaires. La LCU fait le lien entre le réseau de communication central et les lampadaires terrain. Une LCU gère typiquement 10 à 50 lampadaires. La panne d'une LCU peut mettre hors service tous ses lampadaires rattachés.

**Driver LED**
Alimentation électronique intégrée dans le luminaire qui alimente le module LED. Le driver régule le courant et permet la variation d'intensité (dimming). Il génère de la chaleur — la température driver est un indicateur de santé clé.

**Contrôleur embarqué**
Module électronique intégré dans le lampadaire (ou séparé) qui gère la communication avec la LCU. Il dispose d'une adresse réseau, d'un firmware, et d'une qualité de signal mesurée.

**Coffret d'alimentation**
Armoire électrique regroupant l'alimentation de plusieurs lampadaires ou LCUs dans une zone.

---

## Protocoles et interfaces

**DALI (Digital Addressable Lighting Interface)**
Protocole numérique standardisé pour le contrôle d'éclairage. Permet la commande individuelle ou en groupe, la lecture du statut et de la consommation.

**D4i**
Extension du protocole DALI pour les luminaires intelligents. Permet la lecture des données de monitoring détaillées du driver (température, heures de fonctionnement, consommation). Indique des capacités de diagnostic avancées.

**0-10V**
Interface analogique de variation d'intensité. Tension entre 0V (éteint) et 10V (pleine puissance). Plus simple que DALI mais moins informatif.

**LoRaWAN**
Protocole radio longue portée basse consommation utilisé pour la communication entre LCUs et serveur central. Adapté aux zones à faible connectivité réseau.

**MQTT**
Protocole de messagerie léger pour l'IoT. Utilisé pour la communication temps réel entre les LCUs et la plateforme cloud.

---

## Concepts métier

**Dimming**
Variation de l'intensité lumineuse d'un lampadaire, exprimée en pourcentage (0% = éteint, 100% = pleine puissance). Le dimming permet d'optimiser la consommation énergétique selon les horaires ou le trafic.

**Télémétrie**
Ensemble des mesures techniques remontées automatiquement par un lampadaire : température, luminosité, puissance consommée, courant, tension, heures de fonctionnement. Mesurées périodiquement et stockées en base.

**Commissioning (mise en service)**
Processus de validation terrain d'un nouveau lampadaire installé. Comprend : test de communication, test de dimming, test de mesure, validation GPS, association à une LCU. Un lampadaire n'est opérationnel que si tous les tests sont réussis.

**Health Score (score de santé)**
Indicateur calculé de 0 à 100 représentant l'état de santé d'une LCU. Prend en compte : statut réseau, nombre de lampadaires offline, alertes actives, ancienneté de la synchronisation. Score > 80 = sain, 50-80 = dégradé, < 50 = critique.

**Work Order (bon de travail)**
Document d'intervention technique associé à un ou plusieurs équipements. Suit le cycle : created → assigned → accepted → in_progress → resolved → closed. Comprend description du problème, technicien assigné, priorité, délai.

**Alerte**
Événement déclencheur signalant une anomalie sur un équipement. Sévérités : critical (intervention immédiate), warning (surveillance), info (information). Types : lampadaire_offline, temperature_high, communication_lost, etc.

**Zone**
Regroupement géographique de lampadaires et LCUs. Utilisé pour l'agrégation statistique, la gestion des interventions et l'analyse de performance.

---

## États d'équipements

**online** : L'équipement communique normalement et est opérationnel.
**offline** : L'équipement ne répond plus aux communications. Peut indiquer une panne électrique, réseau ou matérielle.
**maintenance** : L'équipement est volontairement mis hors service pour maintenance. État temporaire.
**discovered** : Lampadaire détecté mais non encore configuré ni commissionné.
**commissioned** : Lampadaire complètement mis en service, tous les tests validés.

---

## Métriques clés

**last_seen_at** : Dernière communication reçue de l'équipement. Si > 15 minutes, l'équipement est considéré offline.
**health_score** : Score de santé LCU (0-100). < 50 = critique, > 80 = sain.
**offline_count** : Nombre de lampadaires offline liés à une LCU ou dans une zone.
**age_hours** : Ancienneté d'un bon de travail en heures depuis sa création.
**driver_temperature** : Température du driver LED en °C. > 70°C = alerte thermique.
**controller_signal_quality** : Qualité du signal du contrôleur (0-100). < 40 = signal faible.
**fault_status** : Code de défaut du lampadaire. NULL = aucun défaut connu.
