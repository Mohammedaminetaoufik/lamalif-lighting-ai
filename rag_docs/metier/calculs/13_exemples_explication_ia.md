---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: exemples_explication
source_code: multiple
audience: admin,technicien,ingenieur
---

# Exemples d'explication IA — Calculs et formules

## Résumé — Format de réponse obligatoire pour les calculs

Quand le LLM répond à une question sur un calcul, il **doit** suivre ce format structuré :

```
### Résultat
[Valeur calculée en gras]

### Formule utilisée
[Formule ou règle en bloc de code]

### Calcul ou explication
[Détail du calcul ou des règles appliquées]

### Interprétation métier
[Ce que le résultat signifie pour l'opérateur]

### Limites / hypothèses
[Ce qui peut rendre ce résultat imprécis ou estimatif]

### Action recommandée (si applicable)
[Ce que l'opérateur doit faire]
```

**7 exemples modèles dans ce document :**
1. Coût énergétique de 71 DH → `59.2 kWh × 1.20 DH/kWh`
2. Priorité LCU KECH-001 → score 75 CRITICAL (offline +40, alertes +20, >30% hors ligne +15)
3. Alerte température critique LP-044 → 78 °C > seuil 75 °C, résolution < 65 °C
4. Pourquoi les économies sont des estimations → linéarité, tarif fixe, données simulées
5. Score réseau 61/100 → `100 − 15 − 20 − 4 = 61 → warning`
6. Indice cause probable LCU/Gateway 0.85 → formule heuristique, forte suspicion
7. CO₂ évité 7.4 tonnes/an → `11 680 kWh × 0.638 kg/kWh`

---

Ce document fournit des paires question/réponse modèles illustrant comment le LLM doit expliquer les calculs de la plateforme. Chaque réponse suit le format structuré attendu : résultat → formule → interprétation → limites.

---

## Exemple 1 — Coût énergétique

**Question :**
> Comment le coût énergétique de 71 DH est-il calculé ?

**Réponse attendue :**

### Résultat
Le coût estimé est **71 DH**.

### Formule utilisée
```
Coût (DH) = Consommation (kWh) × Tarif (DH/kWh)
```

### Calcul
```
59,2 kWh × 1,20 DH/kWh = 71,04 DH ≈ 71 DH
```

### Interprétation métier
Ce montant représente le coût estimé de la consommation électrique du parc sur la période sélectionnée. La consommation de 59,2 kWh est la somme des mesures d'énergie enregistrées par les capteurs des lampadaires.

### Limites
- Le tarif de 1,20 DH/kWh est une valeur de référence. Il doit être configuré selon votre contrat électrique réel avec votre opérateur.
- La consommation est calculée depuis les données de télémétrie. En mode démonstrateur, ces données sont simulées.

---

## Exemple 2 — Priorité LCU

**Question :**
> Pourquoi la LCU KECH-001 est-elle prioritaire ?

**Réponse attendue :**

### Résultat
La LCU KECH-001 a un score de risque de **75/100**, ce qui correspond à une priorité **CRITICAL**.

### Formule utilisée
```
Score LCU = 0
+40 si LCU hors ligne
+20 si alertes critiques présentes
+15 si > 30 % de lampadaires hors ligne
```

### Calcul
```
KECH-001 est hors ligne → +40
3 alertes critiques sur ses lampadaires → +20
8 lampadaires sur 12 hors ligne (67 %) → +15
Score = 75 → CRITICAL
```

### Interprétation métier
La LCU KECH-001 est en défaillance totale : elle ne supervise plus ses 12 lampadaires et 8 d'entre eux sont hors ligne. La règle fondamentale s'applique : intervenir d'abord sur la LCU avant d'envoyer des techniciens sur chaque lampadaire individuellement.

### Action recommandée
1. Vérifier l'alimentation électrique de la LCU KECH-001
2. Tester la connectivité réseau (ping, port 502 Modbus)
3. Si la LCU est alimentée mais hors ligne : vérifier le backhaul réseau
4. Créer un bon de travail urgent pour KECH-001

---

## Exemple 3 — Alerte température critique

**Question :**
> Pourquoi l'alerte température sur LP-044 est-elle critique ?

**Réponse attendue :**

### Résultat
L'alerte **temperature_elevee** sur LP-044 est de sévérité **CRITICAL**.

### Formule utilisée (seuils alertes)
```
DÉCLENCHER si : temperature > 75 °C → CRITICAL
RÉSOUDRE si  : temperature < 65 °C
```

### Explication
La dernière mesure de LP-044 indique **78 °C**, ce qui dépasse le seuil critique de 75 °C. L'alerte restera active tant que la température ne redescend pas sous 65 °C (hystérésis de 10 °C).

### Interprétation métier
Un driver LED à 78 °C est en zone de risque élevé. Au-delà de 75 °C, la durée de vie des condensateurs électrolytiques se dégrade rapidement. Le calculateur de dimming a automatiquement réduit l'intensité à 50 % maximum pour limiter la dissipation thermique.

### Action recommandée
- Vérifier la ventilation du coffret de LP-044
- Si la température persiste > 75 °C malgré la réduction de dimming : intervention terrain urgente
- Vérifier si d'autres lampadaires de la même zone présentent une surchauffe (problème de lot ou de zone climatique)

---

## Exemple 4 — Économies estimées

**Question :**
> Pourquoi les économies sont-elles une estimation et non une mesure exacte ?

**Réponse attendue :**

### Résultat
Les économies affichées sont des **estimations**, pas des mesures exactes.

### Formule utilisée
```
Économie_W = Σ(P_nominale × (1 - intensité/100))
Économie_DH = Économie_kWh × Tarif
```

### Pourquoi c'est une estimation

**1. Hypothèse de linéarité :** La formule suppose que la consommation est exactement proportionnelle à l'intensité de dimming. En réalité, les drivers LED peuvent avoir un comportement non linéaire, surtout aux valeurs extrêmes (0–10 % et 90–100 %).

**2. Tarif fixe :** Le tarif de 1,20 DH/kWh est une référence. Votre contrat réel peut être différent (tranche horaire, tarif négocié).

**3. Données simulées (en mode démonstrateur) :** La consommation est générée par le simulateur, pas par des capteurs réels.

**4. Facteur de puissance non intégré :** La puissance active réelle peut différer légèrement de la puissance calculée si le facteur de puissance du driver est inférieur à 1.

### Conclusion
Les économies affichées donnent un ordre de grandeur fiable pour la prise de décision. Pour des calculs précis (appels d'offres, rapports officiels), une mesure directe par compteur homologué est nécessaire.

---

## Exemple 5 — Score réseau

**Question :**
> Comment le score réseau de 61/100 est-il calculé ?

**Réponse attendue :**

### Résultat
Le score réseau est **61/100**, état : **warning** (dégradé).

### Formule utilisée
```
Score = 100
Score -= (lampadaires_hors_ligne / total) × 60
Score -= min(20, alertes_critiques × 3)
Score -= (LCUs_hors_ligne / total_LCUs) × 20
Score = max(0, Score)
```

### Calcul détaillé
```
Total lampadaires : 120  |  Hors ligne : 30 (25 %)
Alertes critiques : 8
Total LCUs : 10          |  Hors ligne : 2 (20 %)

Score = 100
     -= (30/120) × 60 = 0.25 × 60 = 15
     -= min(20, 8×3) = min(20, 24) = 20
     -= (2/10) × 20 = 0.2 × 20 = 4

Score = 100 - 15 - 20 - 4 = 61
```

### Interprétation métier
Le réseau est en état dégradé (warning). Les 8 alertes critiques représentent la pénalité la plus importante (20 points), suivies des 25 % de lampadaires hors ligne (15 points) et des 2 LCUs hors ligne (4 points).

### Action prioritaire
Traiter d'abord les 8 alertes critiques et les 2 LCUs hors ligne, ce qui permettrait de récupérer 24 points et de passer le score à 85 (état normal).

---

## Exemple 6 — Indice de cause probable

**Question :**
> Que signifie un indice de communication LCU/Gateway à 0.85 ?

**Réponse attendue :**

### Résultat
L'indice de cause probable **"Communication LCU/Gateway"** est de **0.85**.

### Ce que cela signifie
Un indice de 0.85 signifie une **forte suspicion** que la cause principale des pannes observées est un problème de communication entre les LCUs et leur gateway réseau. Ce n'est pas une probabilité statistique calculée sur des données historiques : c'est un indicateur heuristique basé sur les données temps réel.

### Formule utilisée
```
Indice = min(0.95,  0.40 + offline_ratio × 0.50 + lcu_offline_count × 0.08)
```

### Interprétation
L'indice est élevé parce que le taux de lampadaires hors ligne est important ET plusieurs LCUs sont hors ligne simultanément. Cette corrélation est le signe caractéristique d'un problème de réseau plutôt que de pannes matérielles individuelles.

### Ce que cet indice ne dit pas
- Il ne confirme pas que c'est la cause — il oriente le diagnostic
- Il ne tient pas compte de facteurs météorologiques (orage, interférence)
- Il devra être recalibré sur des données terrain réelles

### Action recommandée
Vérifier en priorité la connectivité réseau des LCUs hors ligne avant d'envoyer des techniciens sur les lampadaires individuels.

---

## Exemple 7 — CO₂ évité

**Question :**
> Comment le CO₂ évité est-il calculé ?

**Réponse attendue :**

### Résultat
Le CO₂ évité est estimé à **7,4 tonnes/an**.

### Formule utilisée
```
CO₂_évité (kg) = Énergie_économisée (kWh) × Facteur_CO₂ (kg CO₂/kWh)
```

### Calcul
```
Énergie économisée : 32 kWh/nuit × 365 nuits = 11 680 kWh/an
Facteur CO₂ : 0,638 kg CO₂/kWh (mix électrique marocain indicatif)

CO₂_évité = 11 680 × 0,638 = 7 451 kg ≈ 7,4 tonnes CO₂/an
```

### Interprétation métier
Cette économie correspond à l'équivalent CO₂ de la consommation électrique de plusieurs foyers. Elle est le résultat direct du dimming intelligent qui réduit la consommation du parc.

### Limites importantes
- Le facteur de 0,638 kg CO₂/kWh est indicatif. Il doit être mis à jour selon les publications annuelles de l'ONEE.
- En mode démonstrateur, l'énergie économisée est calculée depuis des données simulées.
- Cette valeur est une estimation pour la communication. Pour des rapports officiels, utiliser les données compteur homologué.

---

## Format de réponse recommandé pour les calculs

Quand le LLM répond à une question sur un calcul, la réponse doit toujours suivre ce format :

```
### Résultat
[Valeur calculée en gras]

### Formule utilisée
[Formule ou règle en bloc de code]

### Calcul ou explication
[Détail du calcul ou des règles appliquées]

### Interprétation métier
[Ce que le résultat signifie pour l'opérateur]

### Limites / hypothèses
[Ce qui peut rendre ce résultat imprécis ou estimatif]

### Action recommandée (si applicable)
[Ce que l'opérateur doit faire]
```
