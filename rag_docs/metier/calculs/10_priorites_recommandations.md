---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: priorites_recommandations
source_code: smart-lighting-ai/app/recommendations/scoring.py,smart-lighting-ai/app/recommendations/formatter.py
audience: admin,technicien,ingenieur
---

# Priorités des recommandations IA

## Objectif métier

Le moteur de recommandations produit des suggestions d'intervention pour l'opérateur et le technicien. Chaque recommandation est associée à une priorité (low / medium / high / critical) qui indique l'urgence de l'action. Cette priorité est calculée automatiquement à partir des scores de risque et ne dépend pas d'un jugement subjectif du LLM.

L'objectif est de permettre à l'opérateur de répondre à : **"Que dois-je faire en premier ?"**

---

## Mapping score → priorité

```
score ≥ 75  →  priorité CRITICAL
score 50–74 →  priorité HIGH
score 25–49 →  priorité MEDIUM
score < 25  →  priorité LOW
```

Ce mapping s'applique aux scores de risque suivants :
- Score de risque lampadaire
- Score de risque LCU
- Score de risque zone
- Score d'efficacité énergétique

---

## Définition des niveaux de priorité

### CRITICAL (score ≥ 75)

**Définition :** Situation nécessitant une intervention immédiate (dans l'heure ou dans les 4 heures).

**Critères typiques :**
- Lampadaire hors ligne + alerte critique + LCU hors ligne (score = 75+)
- Zone avec > 80 % de lampadaires hors ligne
- LCU hors ligne avec alertes critiques

**Action attendue de l'opérateur :**
- Créer immédiatement un bon de travail urgent
- Assigner un technicien disponible
- Notifier le responsable de zone si nécessaire

---

### HIGH (score 50–74)

**Définition :** Intervention requise dans les 24 heures.

**Critères typiques :**
- Lampadaire hors ligne sans alerte critique (score ≈ 30–40)
- LCU avec health score dégradé (score ≈ 50–60)
- Zone avec 40–79 % de lampadaires hors ligne

**Action attendue :**
- Planifier une intervention dans la journée
- Inclure dans la liste des priorités du technicien

---

### MEDIUM (score 25–49)

**Définition :** Intervention planifiable dans les 48–72 heures.

**Critères typiques :**
- Bon de travail non résolu depuis > 48h (score ≈ 15)
- Température driver en zone de surveillance (score ≈ 15)
- LCU avec quelques lampadaires hors ligne (< 30 %)

**Action attendue :**
- Inclure dans la prochaine tournée de maintenance planifiée
- Surveiller si la situation se dégrade

---

### LOW (score < 25)

**Définition :** Aucune urgence, surveillance normale.

**Critères typiques :**
- Lampadaire non mis en service (score = 10)
- Télémétrie légèrement obsolète sans autre incident
- Intensité dimming légèrement élevée mais sans surconsommation

**Action attendue :**
- Aucune action immédiate
- Corriger lors de la prochaine visite de maintenance

---

## Score d'efficacité énergétique

```
score = 100
−25  si intensite_moyenne ≥ 90 % (pas de dimming effectif)
−20  si puissance mesurée > puissance nominale moy × 0.90 (surconsommation)
```

### Interprétation
- **Score 100 :** Dimming actif et consommation normale → pas de recommandation
- **Score 75 :** Dimming peu ou pas utilisé → recommandation d'optimisation (CRITICAL si > 75)
- **Score 80 :** Légère surconsommation → recommandation MEDIUM

Ce score mesure si le système de dimming intelligent est réellement utilisé. Une intensité moyenne de 90 % sur l'ensemble du parc signifie que le dimming automatique n'est pas correctement configuré ou que les profils horaires manquent.

---

## Exemple de recommandation générée

```
Recommandation : "Configurer les profils d'éclairage pour la Zone A"
Raison         : Intensité moyenne = 92 %, aucun profil horaire activé
Score          : 75 → CRITICAL
Économie est.  : 4 500 DH/an (si profil nuit creuse configuré)
```

---

## Comment les recommandations sont-elles générées ?

1. **Collecte des données** : les vues SQL `ai_*` sont interrogées pour récupérer l'état de chaque lampadaire, LCU et zone.
2. **Évaluation des règles** : chaque module de règles (lampadaire, LCU, driver, énergie, maintenance, commissioning, zone) évalue les données et génère des recommandations candidates.
3. **Calcul du score** : le score de risque est calculé pour chaque entité concernée.
4. **Mapping priorité** : le score est converti en priorité (low/medium/high/critical).
5. **Tri** : les recommandations sont triées par priorité décroissante.
6. **Dédoublonnage** : les recommandations redondantes (même entité, même type) sont fusionnées.

---

## Règle absolue : aucune action automatique

Le moteur de recommandations ne déclenche **jamais** d'action automatique :
- Il ne commande pas de dimming
- Il ne crée pas de bon de travail automatiquement
- Il ne coupe pas l'alimentation d'un lampadaire
- Il ne modifie pas les profils d'éclairage

Toutes les recommandations nécessitent une validation humaine avant exécution.

---

## Limites et hypothèses

- Le mapping score → priorité est fixe dans la version actuelle. Une version future devrait permettre de configurer les seuils par client ou par contrat.
- Le score ne tient pas compte de la disponibilité des techniciens ou des contraintes budgétaires.
- Deux lampadaires avec le même score peuvent avoir des causes très différentes (l'un hors ligne pour raison climatique, l'autre pour panne hardware). Le score ne distingue pas ces cas.
- En période de forte chaleur ou de tempête, les scores peuvent être temporairement élevés pour des raisons externes non liées à une défaillance du système.

## Source technique

`smart-lighting-ai/app/recommendations/scoring.py`
`smart-lighting-ai/app/recommendations/formatter.py`
Fonctions : `map_priority(score) → str`, `sort_recommendations(recs) → list`
