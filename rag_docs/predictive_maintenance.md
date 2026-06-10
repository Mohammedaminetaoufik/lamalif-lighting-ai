# Maintenance Prédictive Éclairage Public

## Principe de la maintenance prédictive

La maintenance prédictive consiste à détecter les signes précurseurs de pannes avant qu'elles ne se produisent, en analysant les tendances des données remontées par les LCUs (courant, tension, température, puissance, heures de fonctionnement).

Objectifs :
- Réduire les interventions en urgence (coûteuses)
- Optimiser les tournées de maintenance (regrouper les interventions)
- Éviter les pannes sur zones critiques (carrefours, écoles, hôpitaux)
- Prolonger la durée de vie des équipements par remplacement préventif

## Indicateurs clés surveillés

### 1. Courant de sortie driver (mA)

Le courant de sortie du driver est le paramètre le plus fiable pour détecter une panne lampe.

| Valeur mesurée | Interprétation | Action |
|---------------|----------------|--------|
| 0 mA la nuit (programme ON) | Lampe absente / grillée | Intervention immédiate |
| 0 mA le jour (programme OFF) | Normal | Aucune |
| Courant nominal ± 5% | Fonctionnement normal | Surveillance standard |
| Courant > nominal + 20% | Surconsommation / court-circuit partiel | Alerte, vérification planifiée |
| Courant < nominal - 20% | Déplétion LED, driver en limitation | Surveillance renforcée |
| Courant fluctuant (±30%) | Cyclage / clignotement, driver instable | Alerte urgente |
| Courant présent de jour (programme OFF) | Allumage parasite (day burner) | Alerte, vérification photocellule |

**Règle critique : 0 mA la nuit = lampe hors service.** Cette anomalie est non ambiguë.

**Day burner (allumage de jour)** : courant présent pendant la période où le programme impose l'extinction. Cause habituelle : photocellule défaillante (reste en position "nuit"). Peut multiplier la consommation par 2 à 3 et réduire la durée de vie des LEDs.

### 2. Tension réseau (V)

| Situation | Seuil | Cause probable |
|-----------|-------|----------------|
| Surtension | > 253 V (EN 50160) | Problème réseau distribution |
| Tension basse | < 207 V | Câble sous-dimensionné, perte charge |
| Tension très basse | < 180 V | Défaut câblage, section insuffisante |
| Oscillations tension | ±10% en < 1 min | Charges commutantes voisines |

Une surtension chronique (> 250V) accélère la dégradation des condensateurs électrolytiques du driver.

### 3. Puissance active (W)

| Anomalie | Description | Seuil typique |
|----------|-------------|---------------|
| Consommation nulle malgré commande ON | Lampe hors service | P < 10% Pnominale |
| Surconsommation | Court-circuit partiel ou mauvais driver | P > 130% Pnominale |
| Sous-consommation progressive | Déplétion LEDs (fin de vie) | P < 70% Pnominale sur 12 mois |
| Consommation de jour | Day burner | P > 20W en période éteinte |

La puissance doit être cohérente avec le niveau de dimming commandé. Un écart > 15% entre la puissance théorique (P_nominale × dimming%) et la puissance mesurée est une anomalie.

### 4. Facteur de puissance (cos φ)

| Valeur | État |
|--------|------|
| > 0,92 | Excellent |
| 0,85–0,92 | Bon |
| 0,75–0,85 | Dégradé — vérification recommandée |
| < 0,75 | Mauvais — condensateur en fin de vie probable |
| < 0,60 | Critique — remplacement driver urgent |

La dégradation du facteur de puissance est un signe précoce du vieillissement des condensateurs électrolytiques du driver.

### 5. Température interne driver (°C)

| Valeur | État | Action |
|--------|------|--------|
| < 50°C | Nominal | Surveillance standard |
| 50–70°C | Acceptable | Vérifier ventilation |
| 70–85°C | Avertissement | Inspecter refroidissement, programmer maintenance |
| > 85°C | Critique | Intervention urgente — risque de dommage permanent |
| Hausse soudaine > 20°C | Anomalie thermique | Alerte immédiate |

La température interne dépend fortement de la température ambiante. Une température driver > 75°C en été peut être normale si l'ambiance dépasse 40°C. Comparer avec d'autres lampadaires de la même zone pour contextualiser.

**Loi d'Arrhenius pour les condensateurs** :
- Chaque augmentation de 10°C divise la durée de vie par 2
- Driver nominal 50 000 h à 25°C → 25 000 h à 35°C → 12 500 h à 45°C
- La température est le facteur de vieillissement n°1 pour les drivers LED

### 6. Heures de fonctionnement (working_time)

| Seuil | Recommandation |
|-------|----------------|
| < 20 000 h | Surveillance standard |
| 20 000–30 000 h | Début de surveillance renforcée |
| 30 000–40 000 h | Planifier inspection et maintenance préventive |
| 40 000–50 000 h | Remplacement préventif recommandé |
| > 50 000 h | Remplacement urgent (driver hors garantie) |

Un lampadaire fonctionnant ~12 h/nuit + quelques heures de dimming partiel atteint ~4 000 h/an, soit 40 000 h en 10 ans.

### 7. Compteur de démarrages (start_counter)

Chaque allumage soumet le driver à un stress thermique (inrush current). Un start_counter anormalement élevé indique :
- Clignotement répété (cycling) : driver instable
- Programme horaire mal configuré avec allumages/extinctions fréquents

| Seuil | Interprétation |
|-------|----------------|
| < 5 000 | Normal (1 allumage/nuit × 12 ans) |
| 5 000–10 000 | Acceptable |
| > 10 000 | Anormal — vérifier programme horaire et stabilité driver |
| > 20 000 | Critique — driver probablement en défaut de cycling |

## Patterns d'anomalies et signatures de pannes

### Pattern 1 : Lampe grillée
```
Heure : 21h00 — Programme : ON (100%)
Courant mesuré : 0 mA
Puissance mesurée : 0 W
Tension réseau : 228 V (normale)
→ Diagnostic : lampe absente ou grillée
→ Action : intervention remplacement lampe
```

### Pattern 2 : Allumage parasite (day burner)
```
Heure : 11h30 — Programme : OFF
Courant mesuré : 350 mA
Puissance mesurée : 75 W
→ Diagnostic : photocellule ou programme horaire défaillant
→ Impact : consommation multipliée × 2, durée de vie réduite
→ Action : vérifier photocellule et configuration horaire
```

### Pattern 3 : Driver en fin de vie (condensateur dégradé)
```
Sur 6 mois :
- Facteur de puissance : 0,92 → 0,81 → 0,74 → 0,68
- Température driver : 65°C → 72°C → 79°C
- Courant : stable mais oscillations ± 5%
→ Diagnostic : condensateurs électrolytiques en dégradation
→ Action : planifier remplacement driver dans les 3 mois
```

### Pattern 4 : Clignotement / cycling
```
Start_counter en hausse rapide (+50 démarrages/semaine vs 1 normal)
Courant fluctuant ± 30%
→ Diagnostic : driver instable, thermal cycling ou défaut électronique
→ Action : remplacement driver urgent
```

### Pattern 5 : Surchauffe estivale
```
Température driver : 88°C
Heure : 14h00 en juillet (programme OFF — lampe éteinte)
Puissance mesurée : 0 W
→ Diagnostic : surchauffe passive (boîtier luminaire chauffé par soleil)
→ Impact sur durée de vie : accélération vieillissement condensateurs
→ Action : inspecter dissipation thermique, envisager ventilation
```

### Pattern 6 : Problème réseau électrique
```
Multiple lampadaires dans même zone :
- Tension < 195 V (sous-tension)
- Courant instable sur tous les points
→ Diagnostic : problème réseau électrique commun (câble sous-dimensionné, défaut armoire)
→ Action : signaler au gestionnaire réseau électrique
```

## Scoring de risque pour maintenance prédictive

Le système peut calculer un score de risque de panne par lampadaire sur les 30/60/90 prochains jours :

### Facteurs de risque pondérés
| Facteur | Poids | Calcul |
|---------|-------|--------|
| Heures fonctionnement | 25% | Linéaire 0→100 entre 30 000h et 50 000h |
| Température moyenne (30j) | 20% | 0 si < 65°C, linéaire jusqu'à 100 si > 85°C |
| Facteur de puissance | 20% | 0 si > 0,90, linéaire jusqu'à 100 si < 0,70 |
| Anomalies récentes | 20% | Nombre d'alertes actives × 10 (cap 100) |
| Âge équipement | 15% | Linéaire 0→100 entre 8 ans et 15 ans |

**Score 0–30** : risque faible — surveillance standard
**Score 31–60** : risque modéré — inspection à planifier dans les 6 mois
**Score 61–80** : risque élevé — maintenance préventive dans les 3 mois
**Score 81–100** : risque critique — intervention urgente recommandée

## Algorithmes de détection d'anomalies

### Détection par seuils fixes
Méthode simple : comparer la valeur mesurée à un seuil prédéfini.
Avantage : déterministe, explicable.
Limite : ne détecte pas les dérives progressives.

### Détection par tendance (régression linéaire)
Calculer la pente de dégradation sur 3–12 mois :
- Facteur de puissance : pente < -0,005/mois → alerte précoce
- Température : pente > +0,5°C/mois sur fond plat → alerte

### Détection par comparaison de pairs (peer comparison)
Comparer un lampadaire à ses voisins du même type dans la même zone :
- Si la consommation d'un lampadaire est > 130% de la médiane de sa zone → anomalie
- Si la température d'un lampadaire est > 15°C au-dessus de la médiane locale → anomalie

### Modèles ML
Des études académiques montrent des précisions de 98,8% pour la prédiction de panne sur lampadaires en utilisant des features : courant, tension, température, heures fonctionnement, compteur démarrages.

Modèles adaptés : Random Forest, Gradient Boosting, LSTM (séries temporelles).
Attention : nécessite des données étiquetées (pannes passées documentées).

## Règles de priorité des interventions

1. **Urgence immédiate** : lampe absente sur zone critique (carrefour, école, hôpital) → intervention J+1 max
2. **Urgence élevée** : day burner ou cycling → intervention < 1 semaine (gaspillage et risque d'incendie)
3. **Planifié prioritaire** : température > 85°C ou facteur de puissance < 0,70 → maintenance < 1 mois
4. **Planifié standard** : heures fonctionnement > 40 000h → intégrer prochaine tournée préventive
5. **Surveillance** : score de risque 31–60 → consigner en liste de suivi renforcé

## Intégration avec le système télégestion

Dans le système, les données de maintenance prédictive sont accessibles via :
- `ai_lampadaires_health` : health_score, last_maintenance_date, working_hours
- `ai_alertes_actives` : alertes en cours par type (panne, température, communication)
- `ai_energy_overview` : consommation anormale (day burner, surconsommation)
- `ai_commissioning_status` : état de commissioning (pré-condition à la maintenance)

Les ordres de travail (work orders) créés par le système documentent les interventions effectuées et permettent de calculer le MTTR (Mean Time To Repair) et le MTBF réel terrain.
