---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: causes_probables
source_code: smart-lighting-ai/app/routes/decision_center.py
audience: admin,technicien,ingenieur
---

# Indices de causes probables

## Résumé — Comment sont calculés les indices de causes probables

Les 4 indices sont des **scores heuristiques déterministes** (pas des probabilités statistiques ML). Ils orientent le diagnostic sans le remplacer. Un indice de 0.85 = "forte suspicion", pas "85 % de chance".

**Les 4 formules :**

| Cause | Formule | Min | Max |
|---|---|---|---|
| **Communication LCU/Gateway** | `min(0.95, 0.40 + offline_ratio × 0.50 + lcu_offline_count × 0.08)` | 0.40 | 0.95 |
| **Alimentation réseau** | `min(0.90, 0.40 + offline_ratio × 0.30 + alertes_critiques × 0.04)` | 0.40 | 0.90 |
| **Gateway/Backhaul** | `min(0.85, 0.40 + lcu_offline_count × 0.10)` | 0.40 | 0.85 |
| **Driver LED individuel** | `0.25` (constante) | 0.25 | 0.25 |

**Variables :**
- `offline_ratio` : taux de lampadaires hors ligne (0.0 à 1.0)
- `lcu_offline_count` : nombre de LCUs hors ligne
- `alertes_critiques` : nombre d'alertes critiques ouvertes

**Exemple :** offline_ratio = 0.60, lcu_offline_count = 3 →
Indice LCU = min(0.95, 0.40 + 0.30 + 0.24) = **0.94** → forte suspicion problème communication.

**Règle de lecture :** La cause avec l'indice le plus élevé est à investiguer en priorité. Si plusieurs indices sont proches, la situation est complexe.

---

## Objectif métier

Quand plusieurs lampadaires tombent en panne simultanément, les causes peuvent être multiples : problème de communication LCU/gateway, panne d'alimentation électrique, défaillance réseau backhaul, ou problèmes individuels de driver. Les indices de causes probables aident l'opérateur et le technicien à orienter leur diagnostic vers la cause la plus vraisemblable, avant même d'envoyer une équipe sur le terrain.

**Important :** Ces indices ne sont pas des probabilités statistiques calculées par un modèle de machine learning entraîné sur des données historiques. Ce sont des **scores heuristiques déterministes** calculés à partir des KPIs du réseau en temps réel. Ils orientent le diagnostic mais ne le remplacent pas.

---

## Terminologie

Dans ce document, les valeurs calculées sont appelées :
- **Indice de cause probable** (et non "probabilité")
- **Score heuristique** (et non "probabilité statistique")

Un indice de 0.85 signifie "forte suspicion de cette cause" — pas "85 % de chances que ce soit la cause".

---

## Indice 1 — Problème de communication LCU/Gateway

### Formule
```
Indice = min(0.95,  0.40 + offline_ratio × 0.50 + lcu_offline_count × 0.08)
```

### Variables
- `offline_ratio` : taux de lampadaires hors ligne (0.0 à 1.0), calculé sur l'ensemble du parc
- `lcu_offline_count` : nombre de LCUs hors ligne
- Valeur de base : 0.40 (suspicion initiale présente même sans incident)
- Cap maximal : 0.95 (jamais de certitude absolue)

### Interprétation
Ce problème est suspecté quand un grand nombre de lampadaires tombent en panne en même temps ET que des LCUs sont également hors ligne. La corrélation entre lampadaires hors ligne et LCUs défaillantes est le signe caractéristique d'un problème de communication plutôt que de pannes individuelles.

### Exemple
```
offline_ratio = 0.60 (60 % des lampadaires hors ligne)
lcu_offline_count = 3

Indice = min(0.95, 0.40 + 0.60×0.50 + 3×0.08)
       = min(0.95, 0.40 + 0.30 + 0.24)
       = min(0.95, 0.94) = 0.94
```
→ Forte suspicion de problème LCU/gateway

---

## Indice 2 — Problème d'alimentation réseau

### Formule
```
Indice = min(0.90,  0.40 + offline_ratio × 0.30 + alertes_critiques × 0.04)
```

### Variables
- `offline_ratio` : taux de lampadaires hors ligne (0.0 à 1.0)
- `alertes_critiques` : nombre d'alertes critiques ouvertes
- Valeur de base : 0.40
- Cap maximal : 0.90

### Interprétation
Un problème d'alimentation se traduit par des pannes groupées avec des alertes critiques de surconsommation ou de tension. Contrairement au problème LCU, ce type de panne n'est pas forcément corrélé à l'état des LCUs.

### Exemple
```
offline_ratio = 0.40
alertes_critiques = 5

Indice = min(0.90, 0.40 + 0.40×0.30 + 5×0.04)
       = min(0.90, 0.40 + 0.12 + 0.20)
       = min(0.90, 0.72) = 0.72
```
→ Suspicion modérée, à investiguer conjointement avec LCU/gateway

---

## Indice 3 — Problème Gateway/Backhaul réseau

### Formule
```
Indice = min(0.85,  0.40 + lcu_offline_count × 0.10)
```

### Variables
- `lcu_offline_count` : nombre de LCUs hors ligne
- Valeur de base : 0.40
- Cap maximal : 0.85

### Interprétation
Quand plusieurs LCUs tombent en panne simultanément sans que les lampadaires individuels semblent défaillants, la cause probable est un problème du réseau de transport (backhaul IP, routeur, serveur de collecte). Si la LCU est alimentée mais ne communique pas, c'est un signe de problème réseau plutôt que matériel.

### Exemple
```
lcu_offline_count = 4

Indice = min(0.85, 0.40 + 4×0.10)
       = min(0.85, 0.40 + 0.40)
       = min(0.85, 0.80) = 0.80
```
→ Suspicion élevée de problème backhaul

---

## Indice 4 — Problème Driver LED individuel

### Formule
```
Indice = 0.25  (constante)
```

### Interprétation
Les pannes de driver LED sont la cause la plus courante de défaillances individuelles mais ne produisent pas de pannes groupées. Cet indice constant de 0.25 reflète une suspicion de base : dans tout réseau actif, un certain pourcentage de drivers se dégrade en permanence. Cet indice doit être renforcé si l'analyse individuelle des lampadaires révèle des alertes de température driver ou de surconsommation.

---

## Tableau des indices

| Cause | Indice min | Indice max | Signal déclencheur |
|---|---|---|---|
| Communication LCU/Gateway | 0.40 | 0.95 | Pannes groupées + LCUs hors ligne |
| Alimentation réseau | 0.40 | 0.90 | Pannes groupées + alertes critiques |
| Gateway/Backhaul | 0.40 | 0.85 | LCUs multiples hors ligne |
| Driver LED individuel | 0.25 | 0.25 | Toujours présent (baseline) |

---

## Comment utiliser ces indices pour le diagnostic

### Étape 1 : Lire les indices dans le Decision Center
Les 4 indices sont affichés avec des barres de progression dans le widget IA.

### Étape 2 : Identifier la cause dominante
La cause avec l'indice le plus élevé est la plus probable. Si plusieurs indices sont proches, la situation est complexe.

### Étape 3 : Actions selon la cause dominante

| Cause dominante | Action prioritaire |
|---|---|
| Communication LCU/Gateway | Vérifier la connectivité de la LCU, redémarrer si nécessaire, tester la communication radio |
| Alimentation réseau | Vérifier les disjoncteurs, mesurer la tension secteur, contrôler les coffrets d'alimentation |
| Gateway/Backhaul | Vérifier le réseau IP (routeur, switch, serveur), tester la connexion depuis la LCU |
| Driver LED | Inspecter les lampadaires individuels avec alertes de température ou surconsommation |

### Étape 4 : Valider sur le terrain
Ces indices ne remplacent pas une intervention physique. Ils permettent de **prioriser** et **orienter** le diagnostic, pas de le conclure.

---

## Ce que ces indices ne font pas

- Ils ne garantissent pas que la cause identifiée est la bonne
- Ils ne remplacent pas une mesure électrique terrain
- Ils ne tiennent pas compte de l'historique des pannes (analyse de récurrence)
- Ils peuvent être trompeurs lors d'incidents atypiques (acte de vandalisme, coupure secteur programmée)
- Ils n'intègrent pas les facteurs météorologiques (orage, foudre)

---

## Limites et hypothèses

- Les formules ont été conçues de manière heuristique : elles n'ont pas été entraînées sur des données historiques de pannes réelles.
- La valeur de base de 0.40 pour les 3 premières causes est arbitraire et devra être ajustée lors d'une phase de calibration avec des données terrain.
- En mode simulateur, les indices reflètent la configuration des scénarios de simulation, pas des pannes réelles.
- Une seule cause peut contribuer à plusieurs indices élevés simultanément (une coupure réseau peut faire tomber les LCUs ET les lampadaires).

## Source technique

`smart-lighting-ai/app/routes/decision_center.py`
Fonctions : `_compute_probable_causes()`, `get_decision_center()`
