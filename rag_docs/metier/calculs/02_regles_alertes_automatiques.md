---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: alertes_automatiques
source_code: smart-lighting-web/backend/internal/services/alert_rules.go
audience: admin,technicien,ingenieur
---

# Règles d'alertes automatiques

## Résumé — Comment fonctionnent les alertes automatiques

Le moteur d'alertes surveille en continu la télémétrie et déclenche des alertes dès qu'un seuil est dépassé. Il utilise le principe d'**hystérésis** : le seuil de résolution est différent (plus bas) du seuil de déclenchement pour éviter les oscillations.

**Les 4 alertes du système :**

| Alerte | Seuil déclenchement | Seuil résolution | Sévérité |
|---|---|---|---|
| Température élevée | température > **75 °C** | température < **65 °C** | **CRITICAL** |
| Humidité élevée | humidité > **85 %** | humidité < **75 %** | WARNING |
| Consommation anormale | puissance > nominal × **1.30** | puissance < nominal × **1.20** | WARNING |
| Consommation critique | puissance > nominal × **1.50** | — | **CRITICAL** |

**Hystérésis :** écart de 10 °C / 10 % entre déclenchement et résolution — l'alerte reste active tant que le seuil de résolution n'est pas atteint.

**Lien avec le dimming :** Quand l'alerte température CRITICAL est active, le calculateur applique automatiquement la règle 2 (intensité ≤ 50 %) pour réduire la chaleur.

**Exemple escalade consommation (lampadaire 100 W) :**
- 135 W → WARNING (> 130)
- 160 W → CRITICAL (> 150, escalade)
- 115 W → RÉSOLU (< 120)

---

## Objectif métier

Le moteur d'alertes surveille en continu les mesures de télémétrie remontées par les lampadaires et déclenche automatiquement des alertes lorsqu'une valeur dépasse un seuil critique. Ces alertes permettent à l'opérateur d'intervenir avant qu'une panne grave survienne.

Les alertes sont **déclenchées et résolues par le code Go** (`alert_rules.go`). Le LLM peut expliquer pourquoi une alerte existe et ce qu'elle signifie.

---

## Concept clé : l'hystérésis

L'hystérésis est la différence volontaire entre le seuil de déclenchement d'une alerte et son seuil de résolution. Ce mécanisme évite les oscillations : sans hystérésis, un capteur qui fluctue autour du seuil déclencherait et résoudrait l'alerte à chaque mesure, créant un bruit inutile.

**Exemple :**
- Déclenchement : température > 75 °C
- Résolution : température < 65 °C
- Écart d'hystérésis : 10 °C

Tant que la température ne redescend pas sous 65 °C, l'alerte reste active même si la température passe brièvement sous 75 °C.

---

## Alerte 1 — Température élevée

### Formule
```
DÉCLENCHER si : temperature > 75 °C
RÉSOUDRE si  : temperature < 65 °C
```

### Sévérité : **CRITICAL**

### Variables
- `temperature` : température du driver LED (°C), issue de `sensor_measurements.temperature`
- `puissance_nominale` : puissance nominale du lampadaire (W), issue de `lampadaires.puissance`

### Interprétation métier
Une température driver supérieure à 75 °C est un seuil d'alarme industriel pour les drivers LED. Au-delà, le condensateur électrolytique du driver se dégrade rapidement, réduisant sa durée de vie. À 90 °C et plus, le risque de panne définitive est immédiat. Cette alerte est CRITICAL car elle peut précéder une panne matérielle coûteuse.

**Action recommandée :** Vérifier la ventilation du coffret, réduire l'intensité (le calculateur le fait automatiquement via la règle 2), envoyer un technicien si la température persiste.

### Exemple simple
```
Mesure 1 : 72 °C → pas d'alerte
Mesure 2 : 76 °C → ALERTE DÉCLENCHÉE (76 > 75)
Mesure 3 : 74 °C → alerte TOUJOURS ACTIVE (74 > 65)
Mesure 4 : 63 °C → ALERTE RÉSOLUE (63 < 65)
```

### Lien avec le dimming
Quand cette alerte est active, le calculateur de dimming (règle 2) réduit automatiquement l'intensité à max 50 %, ce qui aide à baisser la température driver.

---

## Alerte 2 — Humidité élevée

### Formule
```
DÉCLENCHER si : humidite > 85 %
RÉSOUDRE si  : humidite < 75 %
```

### Sévérité : **WARNING**

### Variables
- `humidite` : taux d'humidité relative dans le coffret (%), issue de `sensor_measurements.humidite`

### Interprétation métier
Une humidité supérieure à 85 % dans le coffret d'un lampadaire peut provoquer une condensation sur les composants électroniques, entraînant des courts-circuits ou une corrosion prématurée. La sévérité WARNING (et non CRITICAL) indique un risque à moyen terme, pas d'urgence immédiate.

**Action recommandée :** Inspecter le joint d'étanchéité du coffret, vérifier si l'humidité est localisée (zone humide, infiltration) ou généralisée (problème de lot).

### Exemple simple
```
Mesure capteur : 88 % → ALERTE WARNING déclenchée
Après séchage  : 70 % → ALERTE RÉSOLUE
```

---

## Alerte 3 — Consommation anormale (WARNING)

### Formule
```
DÉCLENCHER si : puissance > puissance_nominale × 1.30
RÉSOUDRE si  : puissance < puissance_nominale × 1.20
```

### Sévérité : **WARNING**

### Variables
- `puissance` : puissance consommée mesurée (W), issue de `sensor_measurements.puissance`
- `puissance_nominale` : puissance nominale du lampadaire (W), issue de `lampadaires.puissance`

### Calcul détaillé
```
seuil_declenchement = puissance_nominale × 1.30
seuil_resolution    = puissance_nominale × 1.20

Exemple : lampadaire 100 W nominal
  seuil_declenchement = 130 W
  seuil_resolution    = 120 W
```

### Interprétation métier
Une surconsommation de 30 % indique un dysfonctionnement du driver (régulation défaillante), une mauvaise programmation du profil d'éclairage (intensité trop élevée), ou un problème électrique (facteur de puissance dégradé). Ce n'est pas encore critique mais signale une anomalie à surveiller.

**Causes possibles :**
- Driver en mode dégradé (régulation de courant défaillante)
- Profil d'éclairage mal configuré (intensité > nominal)
- Problème de tension réseau (surtension)
- Facteur de puissance dégradé (harmoniques)

---

## Alerte 4 — Consommation anormale (CRITICAL — escalade)

### Formule
```
DÉCLENCHER si : puissance > puissance_nominale × 1.50
```

### Sévérité : **CRITICAL** (escalade depuis WARNING)

### Interprétation métier
Une surconsommation de 50 % ou plus signale une défaillance grave du driver ou un court-circuit. Le risque d'incendie ou de destruction du matériel est réel. Cette alerte nécessite une intervention immédiate.

**Action recommandée :** Couper l'alimentation du lampadaire concerné, envoyer un technicien en urgence, vérifier le driver et le câblage.

### Exemple avec escalade
```
Lampadaire 100 W nominal :
  Mesure 120 W → pas d'alerte (< 130 W)
  Mesure 135 W → ALERTE WARNING (135 > 130)
  Mesure 160 W → ALERTE CRITICAL (160 > 150) — escalade
  Mesure 125 W → retour à WARNING (125 > 120 donc non résolu)
  Mesure 115 W → ALERTE RÉSOLUE (115 < 120)
```

---

## Tableau récapitulatif des alertes

| Alerte | Seuil déclenchement | Seuil résolution | Sévérité | Hystérésis |
|---|---|---|---|---|
| Température élevée | > 75 °C | < 65 °C | CRITICAL | 10 °C |
| Humidité élevée | > 85 % | < 75 % | WARNING | 10 % |
| Consommation anormale | > nominal × 1.30 | < nominal × 1.20 | WARNING | 10 % nominal |
| Consommation critique | > nominal × 1.50 | — | CRITICAL | — |

---

## Différence entre WARNING et CRITICAL

| Niveau | Signification | Délai d'intervention |
|---|---|---|
| **WARNING** | Anomalie à surveiller, risque à moyen terme | Sous 48h |
| **CRITICAL** | Risque immédiat, équipement ou sécurité en danger | Immédiat (< 4h) |

---

## Limites et hypothèses

- Les seuils (75 °C, 85 %, ×1.30, ×1.50) sont des valeurs de référence à calibrer selon le type d'équipement et les conditions d'installation.
- La télémétrie est actuellement simulée en mode démonstrateur. En production, des données réelles peuvent révéler des seuils différents selon la marque du driver ou la zone climatique.
- Une alerte fréquemment déclenchée et résolue peut indiquer un problème de calibration du capteur ou une variabilité normale du réseau électrique.
- La consommation nominale doit être correctement renseignée dans la table `lampadaires.puissance` pour que le calcul soit précis.

## Source technique

`smart-lighting-web/backend/internal/services/alert_rules.go`
Fonction : `RunAlertRules(lamp, telemetry, db) → []Alert`
