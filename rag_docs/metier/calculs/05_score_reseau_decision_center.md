---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: score_reseau
source_code: smart-lighting-ai/app/routes/decision_center.py
audience: admin,technicien,ingenieur
---

# Score réseau — Decision Center IA

## Objectif métier

Le score réseau est un indicateur synthétique de la santé globale du réseau de lampadaires. Il est calculé sur une échelle de 0 à 100, où 100 représente un réseau parfaitement fonctionnel et 0 représente un réseau en défaillance totale.

Ce score est affiché dans le widget "Centre de décision IA" du dashboard et permet à l'opérateur d'évaluer en un coup d'œil l'état général de son parc, sans avoir à parcourir tous les lampadaires individuellement.

Ce calcul est **exécuté par le service Python FastAPI** (`decision_center.py`). Il est 100 % déterministe et rule-based : aucun LLM n'est impliqué dans ce calcul.

---

## Formule du score réseau

```
Score = 100

Score -= (lampadaires_hors_ligne / total_lampadaires) × 60
Score -= min(20, alertes_critiques × 3)
Score -= (LCUs_hors_ligne / total_LCUs) × 20

Score = max(0, Score)
```

### Décomposition des pénalités

| Pénalité | Formule | Maximum | Raison |
|---|---|---|---|
| Lampadaires hors ligne | `(hors_ligne / total) × 60` | 60 pts | Impacte directement le service rendu |
| Alertes critiques | `min(20, nb_critiques × 3)` | 20 pts | Chaque alerte critique = 3 pts, cap à 20 |
| LCUs hors ligne | `(LCUs_hs / total_LCUs) × 20` | 20 pts | Une LCU hors ligne impacte plusieurs lampadaires |

### Pourquoi ces pondérations ?

- **60 points pour les lampadaires :** La mission principale du réseau est l'éclairage. Un réseau où la majorité des lampadaires est hors ligne a failli à son objectif primaire.
- **20 points pour les alertes critiques :** Chaque alerte critique représente un risque pour l'équipement. Le cap à 20 points évite qu'un nombre anormalement élevé d'alertes (tempête, coupure secteur) efface complètement le score.
- **20 points pour les LCUs :** Une LCU hors ligne prive plusieurs lampadaires de communication et de supervision, même si les lampadaires s'allument encore via leur timer interne.

---

## Classification du score

| Score | État | Signification |
|---|---|---|
| ≥ 71 | **normal** | Réseau fonctionnel, incidents mineurs possibles |
| 41 – 70 | **warning** | Dégradation significative, surveillance renforcée |
| ≤ 40 | **critical** | Défaillance majeure, intervention urgente requise |

---

## Formule de confiance

La confiance indique dans quelle mesure le score est représentatif de la réalité du réseau. Un score calculé avec peu de données de supervision est moins fiable.

```
Confiance = 0.72 + (couverture × 0.23)

couverture = (nb_zones_saines × 8 + nb_LCUs_saines × 4) / total_lampadaires
```

### Interprétation de la confiance
- **Confiance ≥ 0.90 :** Score très fiable, bonne couverture de supervision
- **Confiance 0.75–0.89 :** Score fiable, quelques zones sans données
- **Confiance < 0.75 :** Score à interpréter avec précaution, données insuffisantes

La valeur de base 0.72 représente la confiance minimale même sans données de supervision (les KPIs de base sont toujours disponibles).

---

## Exemple complet

**Situation :**
- Total lampadaires : 120
- Hors ligne : 30
- Alertes critiques : 8
- Total LCUs : 10
- LCUs hors ligne : 2

**Calcul :**
```
Score = 100
Score -= (30 / 120) × 60 = 0.25 × 60 = 15
Score -= min(20, 8 × 3) = min(20, 24) = 20
Score -= (2 / 10) × 20 = 0.2 × 20 = 4

Score = 100 - 15 - 20 - 4 = 61
```

**Résultat : Score = 61 → État "warning"**

---

## Interprétation détaillée des pénalités

### Pourquoi les lampadaires hors ligne pénalisent jusqu'à 60 points ?

Un réseau où 100 % des lampadaires sont hors ligne perd 60 points (100 % × 60 = 60). Il lui reste un score de 40 — toujours "critical". La pénalité maximale de 60 (et non 100) reflète que même sans lampadaires, les LCUs et la supervision peuvent encore fonctionner partiellement.

### Pourquoi les alertes critiques sont limitées à 20 points ?

Le cap à 20 points (`min(20, nb × 3)`) correspond à environ 7 alertes critiques. Au-delà, la situation est déjà critique sans que le score aille à zéro. Ce cap évite les distorsions lors d'incidents réseau massifs (coupure secteur généralisée) où de nombreuses alertes peuvent être générées simultanément pour une seule cause.

### Pourquoi les LCUs hors ligne pénalisent ?

Une LCU hors ligne ne signifie pas forcément que ses lampadaires sont éteints (ils peuvent fonctionner en mode standalone). Mais elle signifie qu'ils ne sont plus supervisés, contrôlés ni mis à jour en temps réel. La perte de contrôle est pénalisée à hauteur de 20 % de l'impact total.

---

## Ce que le score ne mesure pas

- La qualité de l'éclairage (luminosité effective au sol)
- L'efficacité du dimming (si les lampadaires sont trop brillants pour l'heure)
- L'âge et l'usure des équipements
- La consommation énergétique (mesuré séparément)
- La satisfaction des usagers

---

## Limites et hypothèses

- Le score suppose que tous les lampadaires ont la même importance (pondération uniforme). En réalité, un lampadaire sur un axe routier principal est plus critique qu'un lampadaire dans un parc.
- Les données sont issues des vues SQL `ai_global_kpis`, `ai_zone_health`, `ai_lcu_health`. Si ces vues sont incomplètes ou retardées, le score peut ne pas refléter l'état temps réel.
- En mode démonstrateur avec données simulées, le score reflète la qualité de la simulation, pas d'une situation terrain réelle.
- Le score est mis en cache pendant 5 minutes pour éviter les recalculs fréquents.

## Source technique

`smart-lighting-ai/app/routes/decision_center.py`
Fonctions : `_compute_network_score()`, `_compute_confidence()`, `get_decision_center()`
