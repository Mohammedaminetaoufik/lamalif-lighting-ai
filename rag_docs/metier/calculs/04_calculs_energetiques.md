---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: calculs_energetiques
source_code: smart-lighting-web/backend/internal/controllers/dashboard.go,smart-lighting-web/backend/internal/repository/stats.go
audience: admin,technicien,ingenieur
---

# Calculs énergétiques

## Résumé — Comment sont calculées l'énergie, les économies et les coûts

Tous les calculs énergétiques sont effectués par le code Go (`dashboard.go`, `stats.go`). Le LLM explique les formules — il ne recalcule pas les valeurs.

**Les 11 formules clés :**

| Calcul | Formule | Unité |
|---|---|---|
| Énergie par mesure (5 min) | `P (W) × 5 / 60 / 1000` | kWh |
| Énergie par heure | `P (W) × (1/12) / 1000` | kWh/h |
| Énergie journalière | `Σ(energie)` toutes mesures du jour | kWh |
| Puissance nominale totale | `Σ(P_nominale)` tous lampadaires actifs | W |
| Puissance actuelle estimée | `Σ(P_nominale × intensité / 100)` | W |
| Économie en watts | `P_nominale_totale − P_actuelle` | W |
| Économie en % | `(Économie_W / P_nominale_totale) × 100` | % |
| Intensité moyenne | `AVG(intensite)` tous lampadaires actifs | % |
| **Coût estimé** | `kWh × 1.20 DH/kWh` | DH |
| Gain dimming | `kWh_économisé × tarif` | DH |
| **CO₂ évité** | `kWh_économisé × 0.638 kg CO₂/kWh` | kg CO₂ |

**Tarifs de référence (configurables) :** 1.20 DH/kWh (Maroc), 0.638 kg CO₂/kWh (ONEE indicatif).

**Formules recommandations :**
- Absence profil dimming : `total_W × 0.45 × 5h / 1000` kWh économisé estimé
- Intensité fixe élevée : `high_W × 0.30 × 8h / 1000` kWh économisé estimé

**Exemple :** 59.2 kWh × 1.20 = **71 DH** estimé. 32 kWh/nuit × 0.638 × 365 = **7.4 tonnes CO₂/an**.

**Hypothèse clé :** relation linéaire `P = P_nominal × intensité/100` (approximation — non parfaite pour tous drivers).

---

## Objectif métier

Les calculs énergétiques permettent à l'opérateur de mesurer la consommation électrique du parc de lampadaires, d'estimer les économies réalisées grâce au dimming intelligent, de calculer le coût en dirhams (DH) et d'évaluer l'impact environnemental en CO₂ évité.

**Ces calculs sont des estimations.** Ils sont calculés par le code Go (dashboard.go, stats.go) à partir des mesures disponibles. Le LLM explique les formules et les interprète — il ne recalcule jamais ces valeurs.

---

## Formule 1 — Énergie par mesure (5 minutes)

### Formule
```
Énergie (kWh) = Puissance (W) × 5 / 60 / 1000
```

### Explication
Chaque mesure de télémétrie correspond à un intervalle de 5 minutes (1/12 d'heure).
- Conversion en heures : 5 / 60
- Conversion en kWh : / 1000

### Exemple
```
Lampadaire 150 W, mesure à t=22h00
Énergie = 150 × 5 / 60 / 1000 = 0.0125 kWh
```

---

## Formule 2 — Énergie par heure

### Formule
```
Énergie (kWh/h) = Puissance (W) × (1/12) / 1000
```
Une heure contient 12 mesures de 5 minutes.

### Exemple
```
Lampadaire 100 W pendant 1 heure
Énergie = 100 × (1/12) / 1000 = 0.00833 kWh/h par mesure
Total sur 1h (12 mesures) = 0.00833 × 12 = 0.1 kWh
```

---

## Formule 3 — Énergie journalière

### Formule
```
Énergie_jour (kWh) = Σ(energie) pour toutes les mesures du jour
```
L'énergie journalière est la somme de toutes les mesures d'énergie enregistrées dans `sensor_measurements` pour un lampadaire ou un groupe donné sur 24 heures.

### Fallback si le champ énergie est absent ou nul
```
Énergie_jour = Σ(puissance) × 5 / 60 / 1000
```
Ce fallback est utilisé quand le compteur d'énergie du capteur n'est pas disponible.

---

## Formule 4 — Puissance totale nominale du parc

### Formule
```
P_nominale_totale (W) = Σ(puissance_nominale) pour tous les lampadaires actifs
```

### Variables
- `puissance_nominale` : puissance nominale de chaque lampadaire, issue de `lampadaires.puissance`
- Lampadaires archivés exclus (`archived_at IS NULL`)

### Exemple
```
100 lampadaires × 100 W (nominal) = 10 000 W = 10 kW nominal total
```

---

## Formule 5 — Puissance actuelle estimée

### Formule
```
P_actuelle (W) = Σ(puissance_nominale × intensite / 100)
```

### Variables
- `intensite` : niveau de dimming actuel du lampadaire (0–100 %), issu de `lampadaires.intensite`

### Exemple
```
Lampadaire 100 W à 60 % d'intensité → contribution = 60 W
Σ sur 100 lampadaires = estimation de la puissance actuelle du parc
```

**Attention :** Cette formule suppose une relation linéaire parfaite entre l'intensité du dimming et la puissance consommée. En réalité, cette relation dépend du type de driver (DALI, 0-10V) et peut ne pas être parfaitement linéaire.

---

## Formule 6 — Économie en watts

### Formule
```
Économie_W (W) = P_nominale_totale - P_actuelle
```

### Interprétation
Représente la puissance que le parc consommerait si tous les lampadaires tournaient à 100 % moins ce qu'ils consomment réellement.

---

## Formule 7 — Économie en pourcentage

### Formule
```
Économie_% = (Économie_W / P_nominale_totale) × 100
```

### Exemple
```
P_nominale_totale = 10 000 W
P_actuelle = 6 000 W
Économie_W = 4 000 W
Économie_% = (4 000 / 10 000) × 100 = 40 %
```

---

## Formule 8 — Intensité moyenne du parc

### Formule
```
Intensité_moyenne (%) = AVG(intensite) sur tous les lampadaires actifs
```

---

## Formule 9 — Coût estimé en dirhams

### Formule
```
Coût (DH) = Consommation (kWh) × Tarif (DH/kWh)
```

### Tarif actuel
```
Tarif = 1.20 DH/kWh
```

**Ce tarif est une valeur de référence.** Il doit être configuré selon le contrat électrique réel de la municipalité. Le tarif peut varier selon la tranche de consommation, l'heure (heures pleines/creuses) et les conditions tarifaires de l'opérateur électrique.

### Exemple
```
Consommation journalière : 59.2 kWh
Tarif : 1.20 DH/kWh
Coût estimé = 59.2 × 1.20 = 71.04 DH ≈ 71 DH
```

---

## Formule 10 — Gain estimé grâce au dimming

### Formule
```
Gain (DH) = Énergie_économisée (kWh) × Tarif (DH/kWh)
Énergie_économisée = (P_nominale_totale - P_actuelle) × Durée (h) / 1000
```

### Exemple
```
Économie puissance : 4 000 W = 4 kW
Durée d'utilisation : 8 heures/nuit
Énergie économisée : 4 kW × 8 h = 32 kWh/nuit
Gain = 32 × 1.20 = 38.40 DH/nuit
Gain annuel (365 nuits) = 38.40 × 365 ≈ 14 016 DH/an
```

---

## Formule 11 — CO₂ évité

### Formule
```
CO₂_évité (kg) = Énergie_économisée (kWh) × Facteur_CO₂ (kg CO₂/kWh)
```

### Facteur CO₂ de référence (Maroc)
Le facteur d'émission moyen du réseau électrique marocain est d'environ **0.638 kg CO₂/kWh** (source : ONEE, données indicatives). Ce facteur est **à configurer** selon les données officielles de l'opérateur électrique national.

### Exemple
```
Énergie économisée : 32 kWh/nuit
Facteur CO₂ : 0.638 kg/kWh
CO₂ évité = 32 × 0.638 = 20.4 kg CO₂/nuit
CO₂ évité annuel = 20.4 × 365 ≈ 7 446 kg = 7.4 tonnes CO₂/an
```

---

## Calculs des recommandations énergétiques

### Recommandation — Absence de profil de dimming
```
Économie estimée (kWh) = total_W × 0.45 × 5h / 1000
```
Hypothèse : un profil de dimming correctement configuré permet une réduction de 45 % de la puissance pendant 5 heures de nuit creuse.

### Recommandation — Intensité fixe élevée (> 80 % sans variation)
```
Économie estimée (kWh) = high_W × 0.30 × 8h / 1000
```
Hypothèse : un dimming adaptatif sur 8 heures permettrait 30 % de réduction.

---

## Tableau récapitulatif

| Calcul | Formule | Unité | Note |
|---|---|---|---|
| Énergie par mesure | P × 5/60/1000 | kWh | Intervalle 5 min |
| Énergie par heure | P × (1/12)/1000 | kWh/h | 12 mesures/heure |
| Énergie journalière | Σ(energie) | kWh | Fallback: Σ(P)×5/60/1000 |
| Puissance nominale totale | Σ(P_nom) | W | Tous lampadaires actifs |
| Puissance actuelle | Σ(P_nom × intensité/100) | W | Estimation linéaire |
| Économie en watts | P_nom - P_actuelle | W | |
| Économie en % | Économie/P_nom × 100 | % | |
| Coût estimé | kWh × 1.20 | DH | Tarif configurable |
| Gain dimming | kWh_économisé × tarif | DH | Estimation |
| CO₂ évité | kWh_économisé × 0.638 | kg CO₂ | Facteur configurable |

---

## Limites et hypothèses importantes

1. **Linéarité du dimming :** La formule `P = P_nominal × intensité/100` suppose une relation linéaire parfaite. En réalité, les drivers LED ne sont pas toujours parfaitement linéaires, surtout aux extrêmes (0–10 % et 90–100 %). Une calibration terrain est nécessaire pour chaque type de driver.

2. **Tarif kWh :** Le tarif de 1.20 DH/kWh est une valeur de référence indicative. Il doit être configuré selon le contrat électrique réel. Une mauvaise valeur produit des estimations de coût incorrectes.

3. **Facteur CO₂ :** La valeur 0.638 kg CO₂/kWh est indicative et varie selon la composition du mix énergétique. Elle doit être mise à jour annuellement depuis les publications officielles de l'ONEE.

4. **Données simulées :** En mode démonstrateur, les mesures proviennent du simulateur. Les calculs sont corrects mais les résultats ne reflètent pas la réalité d'un réseau physique.

5. **Facteur de puissance :** Les formules actuelles ne tiennent pas compte du cos φ (facteur de puissance). La puissance active réelle peut différer de la puissance apparente pour des drivers à faible facteur de puissance.

6. **Intervalle de mesure :** Les calculs supposent un intervalle de 5 minutes. Si l'intervalle de remontée change, les formules doivent être adaptées.

## Source technique

`smart-lighting-web/backend/internal/controllers/dashboard.go`
`smart-lighting-web/backend/internal/repository/stats.go`
Fonctions : `GetDashboardStats()`, `GetEnergyStats()`, `GetTopConsumers()`
