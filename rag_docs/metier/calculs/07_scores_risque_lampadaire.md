---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: score_risque_lampadaire
source_code: smart-lighting-ai/app/recommendations/scoring.py
audience: admin,technicien,ingenieur
---

# Score de risque lampadaire

## Objectif métier

Le score de risque lampadaire quantifie le degré d'urgence d'intervention sur un lampadaire donné. Plus le score est élevé, plus le lampadaire présente des signes de dysfonctionnement cumulés qui nécessitent une intervention rapide.

Ce score aide l'opérateur à répondre à la question : **"Sur lequel de ces 120 lampadaires dois-je intervenir en premier ?"**

Ce calcul est exécuté par le moteur Python (`scoring.py`). Il est déterministe et rule-based.

---

## Formule du score de risque

```
score = 0

+30  si etat == "offline"
+25  si alerte critique ouverte
+20  si LCU associée hors ligne
+15  si bon de travail ouvert depuis > 48h sans résolution
+25  si temperature_driver ≥ 80 °C
+15  si 70 °C ≤ temperature_driver < 80 °C
+10  si dernière télémétrie reçue il y a > 6h
+10  si commissioning_status ≠ "commissioned"

score = min(100, score)  # plafonné à 100
```

---

## Détail des critères

### Critère 1 — État hors ligne (+30)

**Signification :** Le lampadaire ne répond plus à la supervision. Soit il est physiquement éteint et ne devrait pas l'être, soit le capteur ou la communication est en panne.

**Pourquoi 30 points ?** C'est le critère le plus pénalisant après la température critique, car un lampadaire hors ligne manque à sa mission principale (éclairer) et ne peut plus être diagnostiqué à distance.

---

### Critère 2 — Alerte critique ouverte (+25)

**Signification :** Au moins une alerte de sévérité CRITICAL est ouverte sur ce lampadaire (température > 75 °C, consommation > 150 % nominal).

**Pourquoi 25 points ?** Une alerte critique non traitée indique un risque réel pour l'équipement. Combinée avec un état hors ligne, elle donne un score de 55, soit priorité HIGH.

---

### Critère 3 — LCU associée hors ligne (+20)

**Signification :** La passerelle LCU qui gère ce lampadaire est hors ligne. Le lampadaire lui-même peut encore fonctionner en mode autonome (timer interne), mais il ne peut plus être contrôlé ni surveillé.

**Pourquoi 20 points ?** Le lampadaire est "aveugle" du point de vue de la supervision, mais pas nécessairement en panne. La pénalité est modérée pour refléter ce risque indirect.

---

### Critère 4 — Bon de travail non résolu depuis > 48h (+15)

**Signification :** Un bon de travail existe pour ce lampadaire mais n'a pas été résolu en 48 heures. Cela peut indiquer une panne complexe, une ressource manquante, ou un oubli dans le workflow.

**Seuil :** `WO_OLD_HOURS = 48h` (configurable)

---

### Critère 5 — Température driver critique : ≥ 80 °C (+25)

**Signification :** La température driver dépasse 80 °C, seuil de risque élevé pour la durée de vie des composants. À ce niveau, une réduction de la durée de vie du driver de 50 % est typiquement observée.

**Pourquoi 25 points ?** Identique à une alerte critique : c'est une urgence équipement.

### Critère 6 — Température driver élevée : 70–79 °C (+15)

**Signification :** La température est dans la zone de surveillance renforcée. Pas encore critique mais à surveiller.

---

### Critère 7 — Télémétrie obsolète : > 6h (+10)

**Signification :** La dernière mesure de capteur remonte à plus de 6 heures. Le lampadaire ne communique plus ses données, ce qui peut indiquer une panne de communication, un problème LCU, ou un lampadaire éteint.

**Seuil :** `TELEMETRY_STALE_HOURS = 6h` (configurable)

---

### Critère 8 — Non mis en service (+10)

**Signification :** Le lampadaire n'a pas encore complété le workflow de mise en service (`commissioning_status ≠ "commissioned"`). Il peut être en cours d'installation, de test ou de configuration.

**Pourquoi 10 points ?** Un lampadaire non mis en service a un statut opérationnel incertain. Il ne contribue pas pleinement au réseau et peut présenter des problèmes non détectés.

---

## Tableau récapitulatif

| Critère | Points | Signification |
|---|---|---|
| État hors ligne | +30 | Panne complète, mission principale non remplie |
| Alerte critique ouverte | +25 | Risque immédiat pour l'équipement |
| Température ≥ 80 °C | +25 | Risque thermique élevé |
| LCU hors ligne | +20 | Supervision et contrôle impossibles |
| Bon de travail > 48h | +15 | Incident non résolu |
| Température 70–79 °C | +15 | Zone de surveillance renforcée |
| Télémétrie > 6h | +10 | Communication dégradée |
| Non mis en service | +10 | Statut opérationnel incertain |

---

## Mapping score → priorité

| Score | Priorité | Interprétation |
|---|---|---|
| ≥ 75 | **CRITICAL** | Intervention immédiate requise |
| 50–74 | **HIGH** | Intervention dans les 24h |
| 25–49 | **MEDIUM** | Intervention planifiable |
| < 25 | **LOW** | Surveillance, pas d'urgence |

---

## Exemples

### Exemple 1 — Lampadaire en panne sévère
```
LP-044 :
  etat = offline → +30
  alerte critique temperature → +25
  LCU associée hors ligne → +20
  télémétrie > 6h → +10

Score = 85 → CRITICAL
```
Intervention immédiate sur LP-044.

### Exemple 2 — Lampadaire à surveiller
```
LP-112 :
  etat = online
  température = 72 °C → +15
  bon de travail ouvert depuis 52h → +15

Score = 30 → MEDIUM
```
Planifier une visite de vérification.

### Exemple 3 — Lampadaire sain
```
LP-007 :
  etat = online
  pas d'alerte
  télémétrie récente
  LCU en ligne
  mis en service

Score = 0 → LOW
```
Aucune action requise.

---

## Limites et hypothèses

- Tous les critères ont la même pondération relative quelle que soit l'importance stratégique du lampadaire (axe principal vs. ruelle secondaire). Une version future pourrait intégrer un coefficient d'importance de zone.
- La température est issue de la télémétrie : si elle est obsolète (critère 7), la valeur thermique est elle-même incertaine.
- Le score ne capture pas la fréquence des incidents passés (un lampadaire en panne chronique vs. une première panne).
- Un score de 0 ne signifie pas que le lampadaire est parfait — il signifie qu'aucun des critères mesurés ne déclenche une alerte.

## Source technique

`smart-lighting-ai/app/recommendations/scoring.py`
Fonction : `compute_lampadaire_risk_score(lamp_data) → int`
