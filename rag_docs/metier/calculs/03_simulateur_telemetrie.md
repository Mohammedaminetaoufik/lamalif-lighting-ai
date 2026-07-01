---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: simulateur_telemetrie
source_code: smart-lighting-web/backend/internal/services/simulator.go
audience: admin,technicien,ingenieur
---

# Simulateur de télémétrie

## Résumé — Comment fonctionne le simulateur de télémétrie

Le simulateur génère des mesures électriques artificielles cohérentes pour 7 scénarios types. Les données sont **simulées** (pas de capteurs réels). Les formules sont correctes et représentatives, mais les valeurs ne correspondent pas à un réseau physique.

**Formules communes à tous les scénarios :**
```
Courant (A) = Puissance (W) / Tension (V)
Énergie (kWh) = Puissance (W) × 5 / 60 / 1000   [intervalle 5 min]
Tension simulée = 225 + rand(0, 10)  → 225–235 V
Humidité simulée = 45 + rand(0, 20) → 45–65 %
```

**Les 7 scénarios et leur effet sur les calculs :**

| Scénario | Puissance | Alerte déclenchée | Règle dimming appliquée |
|---|---|---|---|
| Nuit normale | 30 % nominal | Aucune | Règle 4 → 30 % |
| Piéton détecté | 90 % nominal | Aucune | Règle 3 → 90 % |
| Véhicule détecté | 100 % nominal | Aucune | Règle 3 → 90 % |
| **Surchauffe** | 60 % nominal | **CRITICAL temp (78 °C > 75 °C)** | Règle 2 → ≤ 50 % |
| Panne driver | 0 W | Possible (éteint) | Règle 7 → 60 % |
| Brûlage diurne | 80 % nominal | Aucune | Règle 6 → 20 % (luminosité > 70 lux) |
| **Surconsommation** | 160 % nominal | **WARNING (> 130 %) + CRITICAL (> 150 %)** | Règle 7 → 60 % |

**Seuils clés :** 75 °C (alerte CRITICAL), 130 % et 150 % nominal (alertes consommation), 70 lux (règle jour).

---

## Objectif métier

Le simulateur de télémétrie génère des mesures électriques cohérentes pour alimenter la plateforme en l'absence de matériel réel connecté. Il permet de tester l'ensemble des workflows (alertes, dimming, rapports énergétiques, bons de travail) avant d'avoir accès à un réseau de lampadaires physiques.

**Important :** Toutes les données produites par ce simulateur sont artificielles. Elles permettent de valider les fonctionnalités de la plateforme mais ne représentent pas des mesures terrain réelles. Les analyses et recommandations générées à partir de ces données sont des démonstrations, pas des diagnostics opérationnels.

---

## Formules électriques communes à tous les scénarios

### Courant
```
Courant (A) = Puissance (W) / Tension (V)
```
Le courant est calculé depuis la puissance et la tension, jamais mesuré directement dans ce simulateur.

### Énergie par mesure (intervalle de 5 minutes)
```
Énergie (kWh) = Puissance (W) × 5 / 60 / 1000
```
Explication : 5 minutes = 5/60 d'heure. 1 kWh = 1000 Wh. Donc :
`Énergie = P(W) × (5/60) / 1000`

**Exemple :** lampadaire 100 W pendant 5 min → `100 × 5/60/1000 = 0.00833 kWh`

### Tension simulée
```
Tension (V) = 225 + rand(0, 10)   → plage : 225–235 V
```
Simule les fluctuations normales du réseau électrique public (tension nominale 230 V ± 5 V).

### Humidité simulée
```
Humidité (%) = 45 + rand(0, 20)   → plage : 45–65 %
```
Représente une humidité relative normale pour un coffret extérieur protégé.

---

## Les 7 scénarios de simulation

### Scénario 1 — Nuit normale

**Objectif :** Simuler le comportement standard d'un lampadaire la nuit sans activité.

| Paramètre | Valeur |
|---|---|
| Puissance | `P_nominal × 30 %` |
| Température | 15 °C |
| Luminosité | 5–15 lux |
| Présence | false |

**Effet sur les calculs :**
- Pas d'alerte température (15 °C << 75 °C)
- Calculateur : règle 4 (nuit sans présence) → intensité 30 %
- Énergie très faible (économie maximale)

---

### Scénario 2 — Piéton détecté

**Objectif :** Simuler la détection d'un piéton et l'augmentation automatique de l'intensité.

| Paramètre | Valeur |
|---|---|
| Puissance | `P_nominal × 90 %` |
| Température | 20 °C |
| Luminosité | 5–15 lux |
| Présence | true |

**Effet sur les calculs :**
- Calculateur : règle 3 (présence + obscurité) → intensité 90 %
- Aucune alerte déclenchée
- Consommation élevée mais justifiée par la sécurité

---

### Scénario 3 — Véhicule détecté

**Objectif :** Simuler le passage d'un véhicule avec intensité maximale.

| Paramètre | Valeur |
|---|---|
| Puissance | `P_nominal × 100 %` |
| Température | 22 °C |
| Luminosité | 2–7 lux |
| Présence | true |

**Effet sur les calculs :**
- Calculateur : règle 3 → intensité 90 % (le 100 % puissance est la simulation, le calculateur cible 90 %)
- Aucune alerte
- Consommation nominale maximale

---

### Scénario 4 — Surchauffe

**Objectif :** Déclencher l'alerte température et tester la protection thermique du calculateur.

| Paramètre | Valeur |
|---|---|
| Puissance | `P_nominal × 60 %` |
| Température | **78 °C** |
| Luminosité | 5 lux |
| Présence | false |

**Effet sur les calculs :**
- **Alerte CRITICAL déclenchée** : 78 °C > 75 °C
- Calculateur : règle 2 → intensité réduite à min(actuelle, 50 %)
- La réduction d'intensité est une réponse automatique pour protéger le driver
- La puissance simulée à 60 % reflète cette réduction

---

### Scénario 5 — Panne driver

**Objectif :** Simuler une panne complète du driver LED (lampadaire éteint mais toujours connecté).

| Paramètre | Valeur |
|---|---|
| Puissance | **0 W** |
| Température | 25 °C |
| Luminosité | **0 lux** |
| Présence | false |

**Effet sur les calculs :**
- Pas d'alerte thermique (température normale)
- La luminosité nulle peut déclencher une alerte de type « lampadaire éteint inattendu »
- Consommation nulle sur ce lampadaire → impact sur les économies calculées
- Bon de travail typiquement créé : investigation driver ou câblage

---

### Scénario 6 — Brûlage diurne

**Objectif :** Simuler un lampadaire allumé pendant la journée (défaut de planification).

| Paramètre | Valeur |
|---|---|
| Puissance | `P_nominal × 80 %` |
| Température | 30 °C |
| Luminosité | **85–95 lux** |
| Présence | false |

**Effet sur les calculs :**
- Calculateur : règle 6 → intensité réduite à 20 % (luminosité > 70 lux)
- Gaspillage d'énergie identifié
- Recommandation IA : configurer un profil horaire pour éviter ce scénario
- La puissance à 80 % dans la simulation représente ce qui se passe avant correction

---

### Scénario 7 — Surconsommation

**Objectif :** Déclencher les alertes de consommation anormale pour tester le workflow d'intervention.

| Paramètre | Valeur |
|---|---|
| Puissance | **`P_nominal × 160 %`** |
| Température | 28 °C |
| Luminosité | 5 lux |
| Présence | false |

**Effet sur les calculs :**
- **Alerte WARNING** : 160 % > 130 % du nominal
- **Alerte CRITICAL** : 160 % > 150 % du nominal (escalade)
- Calculateur : pas de réduction automatique (surchauffe non dépassée)
- Bon de travail urgent créé par l'opérateur

---

## Résumé des scénarios

| Scénario | Puissance | Alerte déclenchée | Règle dimming |
|---|---|---|---|
| Nuit normale | 30 % nominal | Aucune | Règle 4 (30 %) |
| Piéton | 90 % nominal | Aucune | Règle 3 (90 %) |
| Véhicule | 100 % nominal | Aucune | Règle 3 (90 %) |
| Surchauffe | 60 % nominal | CRITICAL temp | Règle 2 (≤50 %) |
| Panne driver | 0 % nominal | Possible | Règle 7 (60 %) |
| Brûlage diurne | 80 % nominal | Aucune | Règle 6 (20 %) |
| Surconsommation | 160 % nominal | WARNING + CRITICAL | Règle 7 (60 %) |

---

## Limites et hypothèses

- Toutes les données sont générées par un générateur pseudo-aléatoire : elles ne proviennent pas de lampadaires physiques.
- Les scénarios sont des cas types simplifiés : les données terrain réelles peuvent être plus complexes et variables.
- Le facteur de puissance (cos φ) n'est pas modélisé dans cette version : la puissance apparente peut différer de la puissance active réelle.
- En conditions réelles, la puissance consommée varie selon la température du filament LED, le vieillissement du driver, la tension réseau effective.
- La durée des mesures est fixée à 5 minutes : une période plus courte ou plus longue modifierait les calculs d'énergie.
- Ce simulateur doit être remplacé par la télémétrie réelle des LCU une fois le hardware connecté.

## Source technique

`smart-lighting-web/backend/internal/services/simulator.go`
Fonction : `GenerateTelemetryScenario(lamp, scenario) → SensorMeasurement`
