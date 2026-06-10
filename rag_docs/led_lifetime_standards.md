# Standards de Durée de Vie LED — LM-80, TM-21, L70, L80

## Introduction

La durée de vie des LEDs est définie de manière standardisée pour permettre des comparaisons objectives entre produits. Contrairement aux lampes à décharge (qui tombent en panne brutalement), les LEDs ne "brûlent" pas mais se déprécie progressivement en termes de flux lumineux — on parle de "lumen depreciation" (dépréciation lumineuse).

Les principaux standards sont développés par l'IES (Illuminating Engineering Society) en Amérique du Nord, adoptés mondialement.

## LM-80 — Mesure du maintien du flux lumineux (IES LM-80)

### Définition
LM-80 est la méthode de test normalisée pour mesurer la dépréciation du flux lumineux d'une source LED (package, module ou array) dans le temps.

### Protocole de test
- Durée minimale : **6 000 heures** de test en continu
- Recommandé : 10 000 heures
- Mesures : toutes les **1 000 heures**
- Températures de test : au minimum 2 températures (55°C et 85°C), souvent 3 (55°C, 85°C, 105°C)
- Courant de test : courant nominal d'utilisation
- Grandeurs mesurées : flux lumineux (lm), tension de forward (Vf), rendement

### Sortie LM-80
Le rapport LM-80 fournit :
- La courbe de dépréciation mesurée : L(t) = flux(t) / flux(0)
- Les données brutes à chaque mesure (utiles pour TM-21)
- Le paramètre "Reported Life" : durée testée

### Limites LM-80
LM-80 ne prédit pas la durée de vie — il ne mesure que ce qui a été observé pendant la période de test. Pour extrapoler au-delà du test, on utilise TM-21.

## TM-21 — Projection de la durée de vie (IES TM-21)

### Définition
TM-21 est la méthode mathématique pour extrapoler la durée de vie LED au-delà de la durée de test LM-80.

### Formule d'extrapolation TM-21
```
L(t) = L₀ × e^(-α × t^β)
```

Où :
- `L(t)` : maintien du flux à l'instant t (en fraction, ex. 0,80 = 80%)
- `L₀` : flux initial normalisé (= 1,00 ou légèrement > 1 pour les LEDs qui brightent avant de décliner)
- `α` : coefficient de dégradation (ajusté par régression sur données LM-80)
- `β` : exposant de forme (β ≈ 1 → déclin linéaire, β < 1 → déclin décroissant, β > 1 → déclin accélérant)
- `t` : temps en heures

### Contrainte R²
La courbe ajustée doit avoir un coefficient de détermination **R² ≥ 0,95** pour que la projection soit valide.

### Règle des 6× (TM-21 extrapolation limit)
TM-21 limite la projection à **6 × la durée testée** LM-80 :
- Si test LM-80 = 6 000 h → projection max = 36 000 h (reporté comme "L70 > 36 000 h")
- Si test LM-80 = 10 000 h → projection max = 60 000 h (reporté comme "L70 > 60 000 h")

Les fabricants qui affichent "L70 = 100 000 h" sur des tests de 6 000 h ne respectent pas TM-21.

## Niveaux de maintien du flux : L70, L80, L90

| Notation | Définition | Application typique |
|----------|------------|---------------------|
| **L90** | 90% du flux initial conservé | Éclairage médical, musées |
| **L80** | 80% du flux initial conservé | Éclairage de qualité (bureau, retail) |
| **L70** | 70% du flux initial conservé | Éclairage extérieur, voirie, industriel |
| **L50** | 50% du flux initial conservé | Décoration (tolérance élevée) |

**En éclairage public**, le critère standard est **L80B50** ou **L70B50** :
- L80 : durée avant d'atteindre 80% du flux nominal
- B50 : 50% des unités testées maintiennent encore ce niveau à cette durée

### Exemples de valeurs typiques éclairage public

| Gamme produit | L80 (Ta=25°C) | L70 (Ta=25°C) | Note |
|---------------|---------------|---------------|------|
| LEDs qualité premium | 60 000 h | > 100 000 h | Module seul |
| Luminaire complet standard | 40 000 h | 60 000–80 000 h | Avec driver |
| Luminaire entrée de gamme | 25 000 h | 40 000 h | |

**Attention** : les valeurs L70/L80 sont données pour le module LED seul à température contrôlée. En conditions réelles (température ambiante > 25°C, cycles thermiques), les durées sont significativement inférieures.

## Taux de défaillance : B10, B50

La notation B (Failure Rate) exprime le pourcentage d'unités défaillantes à un instant donné :

| Notation | Définition |
|----------|------------|
| **B10** | 10% des unités ont atteint la fin de vie à cette durée |
| **B50** | 50% des unités ont atteint la fin de vie à cette durée |

Le couple **LxBy** (ex. L80B50) est le standard complet :
- **L80B50** : après X heures, 50% des unités émettent encore ≥ 80% du flux initial
- **L70B10** : après X heures, 10% des unités ont déjà chuté sous 70% du flux

En pratique sur la voirie, on vise **L80B10** ≥ 25 000 h pour garantir un maintien acceptable sur la majorité du parc.

## Température de jonction et loi d'Arrhenius

### Impact de la température sur la durée de vie LED

La dégradation des LEDs suit la loi d'Arrhenius :
```
Rate of degradation ∝ e^(-Ea / (k × T))
```
Où :
- `Ea` : énergie d'activation (eV) — spécifique au mécanisme de dégradation
- `k` : constante de Boltzmann (8,617 × 10⁻⁵ eV/K)
- `T` : température absolue (Kelvin = °C + 273,15)

**Règle empirique simplifiée** : chaque augmentation de **10°C de la température de jonction** réduit la durée de vie LED de **50%**.

| Température jonction | Multiplicateur durée de vie (vs 25°C) |
|---------------------|--------------------------------------|
| 25°C | × 1 (référence) |
| 35°C | × 0,5 |
| 45°C | × 0,25 |
| 55°C | × 0,125 |
| 65°C | × 0,063 |
| 85°C | × 0,016 |

**Température de jonction (Tj)** n'est pas la température ambiante — elle inclut :
- Température ambiante (Ta)
- Échauffement par la dissipation thermique du driver
- Résistance thermique boîtier → jonction (Rth)

```
Tj = Ta + (P × Rth_JA)
```

Un luminaire conçu pour Ta=25°C peut voir Tj > 85°C en été (Ta=40°C + dissipation driver).

## Durée de vie des condensateurs électrolytiques

Le driver LED est souvent le composant limitant la durée de vie du luminaire — non pas les LEDs elles-mêmes.

### Mécanisme de dégradation
- Les condensateurs électrolytiques (aluminium) perdent leur électrolyte par évaporation
- La perte d'électrolyte augmente l'ESR (Equivalent Series Resistance)
- Un ESR élevé génère plus de chaleur → accélère encore l'évaporation (cycle positif de dégradation)

### Durée de vie nominale condensateurs

| Qualité condensateur | Durée nominale (Ta=105°C) | Durée réelle (Ta=70°C) |
|----------------------|--------------------------|------------------------|
| Standard | 2 000 h | ~16 000 h |
| Long life | 5 000 h | ~40 000 h |
| Ultra long life | 10 000 h | ~80 000 h |

**Calcul simplifié** (règle des 10°C / facteur 2) :
```
Durée_réelle = Durée_nominale × 2^((T_nominale - T_réelle) / 10)
```

Exemple : condensateur 5 000 h à 105°C, Ta réelle = 65°C :
```
Durée = 5 000 × 2^((105-65)/10) = 5 000 × 2^4 = 5 000 × 16 = 80 000 h
```

### Conséquence pour la maintenance

- Les condensateurs de mauvaise qualité (5 000 h à 105°C) en conditions chaudes (65°C) durent ~80 000 h — souvent suffisant
- Mais si la température réelle du driver monte à 85°C (été + dissipation) :
  ```
  Durée = 5 000 × 2^((105-85)/10) = 5 000 × 4 = 20 000 h
  ```
  → Remplacement nécessaire en ~5 ans (4 000 h/an)

- La surveillance de la température driver est donc critique pour anticiper la durée de vie réelle.

## Lumen depreciation et planification de remplacement

### Formule de dépréciation simplifiée (linéaire)
```
Flux(t) = Flux_initial × (1 - taux_annuel × années)
```
Exemple avec taux de dépréciation 2%/an :
- Après 5 ans : 90% du flux initial
- Après 10 ans : 80% (seuil L80)
- Après 15 ans : 70% (seuil L70)

### Facteurs accélérant la dépréciation
1. **Température élevée** (Ta > 35°C) : facteur × 2–4 sur la vitesse de dépréciation
2. **Courant de pilotage élevé** (overdrive > 100% du courant nominal) : dépréciation accélérée
3. **Cycles thermiques** (allumage/extinction fréquents) : contraintes mécaniques sur les soudures
4. **Humidité** : corrosion des contacts, variation du gap optique

### Critère de remplacement lumière

En éclairage public, le remplacement est recommandé quand :
- Le flux mesuré est < 70% du flux initial (critère L70)
- Ou quand l'éclairement moyen sur chaussée tombe sous l'EN 13201 (norme européenne routes)
  - ME3a : Em ≥ 15 lux, Emin ≥ 5 lux (routes principales)
  - ME4a : Em ≥ 10 lux, Emin ≥ 3 lux (routes secondaires)
  - ME5 : Em ≥ 7,5 lux, Emin ≥ 1,5 lux (zones résidentielles)

## Application dans le système télégestion

Les données disponibles dans le système pour estimer la durée de vie restante :

| Donnée | Vue | Usage prédictif |
|--------|-----|-----------------|
| Heures fonctionnement | `ai_lampadaires_health` | Calcul durée de vie consommée |
| Température driver | `ai_lampadaires_details` | Application loi Arrhenius |
| Puissance consommée | `ai_energy_overview` | Détection sous-consommation (dépréciation) |
| Date mise en service | `ai_lampadaires_health` | Âge équipement |
| Compteur démarrages | `ai_lampadaires_details` | Stress thermique cumulé |

### Interprétation : puissance vs dépréciation LED

Quand les LEDs vieillissent, leur efficacité lumineuse diminue. Pour maintenir le niveau d'éclairement, deux stratégies :
1. Le driver augmente le courant automatiquement (capteur de flux en boucle fermée) → la puissance mesurée augmente
2. Le driver maintient le courant constant → le flux diminue (visible sur rapport photométrique terrain)

Un driver avec D4i Part 252 peut mesurer directement la dégradation du flux via retour capteur.

## Résumé des seuils de décision

| Indicateur | Surveiller | Planifier | Urgent |
|------------|-----------|-----------|--------|
| Heures fonctionnement | > 30 000 h | > 40 000 h | > 50 000 h |
| Température driver | > 65°C | > 75°C | > 85°C |
| Facteur de puissance | < 0,85 | < 0,75 | < 0,65 |
| Âge depuis mise en service | > 8 ans | > 12 ans | > 15 ans |
| Puissance vs nominal | ±15% | ±25% | ±35% |
