---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: scores_lcu_zone
source_code: smart-lighting-ai/app/recommendations/scoring.py
audience: admin,technicien,ingenieur
---

# Scores de risque LCU et zone

## Résumé — Comment sont calculés les scores de risque LCU et zone

Deux scores agrégés pour détecter les problèmes **groupés** avant d'intervenir sur les lampadaires individuels. Calculés par `scoring.py`, plafonnés à 100.

**Score de risque LCU :**
```
Score = 0
+40  si LCU hors ligne (status == "offline")
+30  si health_score < 30
+20  si alertes critiques présentes sur les lampadaires de cette LCU
+15  si health_score ∈ [30, 60[
+15  si (lampadaires_hors_ligne / total_lampadaires_LCU) > 30 %
Score = min(100, score)
```

**Score de risque zone :**
```
Score = 0
+60  si (lampadaires_hors_ligne / total_zone) ≥ 80 %  → défaillance quasi-totale
+40  si (lampadaires_hors_ligne / total_zone) ≥ 40 %  → défaillance majeure
+20  si (lampadaires_hors_ligne / total_zone) > 0 %   → pannes ponctuelles
+min(30, alertes_critiques × 10)                      → cap à 30
+10  si bons de travail ouverts dans la zone
Score = min(100, score)
```
Note : les 3 paliers hors ligne (80 %, 40 %, >0 %) sont exclusifs — seul le palier le plus haut atteint s'applique.

**Mapping score → priorité (identique LCU et zone) :**

| Score | Priorité | Action |
|---|---|---|
| ≥ 75 | **CRITICAL** | Intervention immédiate |
| 50–74 | **HIGH** | Dans les 24h |
| 25–49 | **MEDIUM** | Prochaine tournée |
| < 25 | **LOW** | Surveillance normale |

**Règle fondamentale :** Score LCU CRITICAL → intervenir sur la LCU **avant** les lampadaires individuels.

---

## Objectif métier

Une LCU (passerelle radio) supervise en général entre 5 et 30 lampadaires. Une zone géographique regroupe plusieurs dizaines à plusieurs centaines de lampadaires. Ces deux niveaux d'agrégation permettent de détecter des problèmes **groupés** qui ne seraient pas visibles en analysant les lampadaires individuellement.

**Règle fondamentale :** Avant d'envoyer des techniciens sur chaque lampadaire individuellement, vérifier d'abord si le problème est au niveau de la LCU ou de la zone.

---

## Score de risque LCU

### Formule
```
score = 0

+40  si LCU hors ligne (status == "offline")
+30  si health_score < 30
+15  si 30 ≤ health_score < 60
+20  si alertes critiques présentes sur les lampadaires de cette LCU
+15  si (lampadaires_hors_ligne / total_lampadaires_LCU) > 30 %

score = min(100, score)
```

### Variables
- `status` : état de la LCU ("online", "offline", "unknown")
- `health_score` : score de santé de la LCU (0–100), calculé séparément via `ai_lcu_health`
- `alertes_critiques` : nombre d'alertes critiques ouvertes sur les lampadaires gérés par cette LCU
- `lampadaires_hors_ligne` : nombre de lampadaires hors ligne sous cette LCU
- `total_lampadaires_LCU` : nombre total de lampadaires rattachés à cette LCU

---

### Détail des critères LCU

#### LCU hors ligne (+40)
C'est le critère le plus critique : si la LCU est hors ligne, tous ses lampadaires perdent leur supervision et leur contrôle à distance. Même si les lampadaires continuent de s'allumer via leur timer interne, ils ne peuvent plus être dimmés, diagnostiqués ou mis à jour.

**Pourquoi 40 points ?** Une seule LCU hors ligne peut isoler 10–30 lampadaires simultanément. C'est un incident à fort impact.

#### Health score < 30 (+30)
Un health score très faible indique une LCU sévèrement dégradée, même si elle n'est pas encore hors ligne. Elle peut présenter des pertes de paquets fréquentes, des délais de réponse élevés, ou des erreurs de communication répétées.

#### Health score 30–59 (+15)
Zone de surveillance : la LCU fonctionne mais présente des signes de dégradation. À monitorer de près.

#### Alertes critiques sur les lampadaires (+20)
Quand plusieurs lampadaires d'une même LCU déclenchent des alertes critiques simultanément, la LCU elle-même peut être impliquée (profil de dimming mal appliqué, commandes défectueuses).

#### Plus de 30 % de lampadaires hors ligne (+15)
Un taux de pannes de plus de 30 % sur les lampadaires d'une LCU est un signal d'alarme. Cela peut indiquer un problème de communication radio ou une zone géographique touchée par un incident.

---

### Tableau récapitulatif — LCU

| Critère | Points | Impact |
|---|---|---|
| LCU hors ligne | +40 | Supervision totale perdue |
| Health score < 30 | +30 | LCU sévèrement dégradée |
| Alertes critiques | +20 | Risque sur les lampadaires associés |
| > 30 % lampadaires hors ligne | +15 | Zone de panne radio probable |
| Health score 30–59 | +15 | Dégradation en cours |

---

### Mapping score → priorité LCU

| Score | Priorité | Action |
|---|---|---|
| ≥ 75 | CRITICAL | Intervention immédiate, priorité absolue |
| 50–74 | HIGH | Intervention dans les 24h |
| 25–49 | MEDIUM | Planifier une vérification |
| < 25 | LOW | Surveillance normale |

---

### Exemple LCU

```
LCU-KECH-001 :
  status = offline → +40
  health_score = N/A (hors ligne, pas de mesure)
  3 alertes critiques → +20
  8 lampadaires sur 12 hors ligne (67 %) → +15

Score = 40 + 20 + 15 = 75 → CRITICAL
```
→ LCU-KECH-001 est prioritaire. Envoyer un technicien sur la LCU avant d'intervenir sur les lampadaires individuellement.

---

## Score de risque zone

### Formule
```
score = 0

+60  si (lampadaires_hors_ligne / total_lampadaires_zone) ≥ 80 %
+40  si (lampadaires_hors_ligne / total_lampadaires_zone) ≥ 40 %
+20  si (lampadaires_hors_ligne / total_lampadaires_zone) > 0 %
     (uniquement si les seuils 80 % et 40 % ne sont pas atteints)
+min(30, alertes_critiques × 10)
+10  si bons de travail ouverts dans cette zone

score = min(100, score)
```

**Note sur les seuils de taux de panne :** Les trois paliers (80 %, 40 %, >0 %) sont **exclusifs** : seul le palier le plus haut atteint contribue.

---

### Détail des critères zone

#### 80 % + lampadaires hors ligne (+60)
Une zone où plus de 80 % des lampadaires sont hors ligne est en état de défaillance quasi-totale. L'éclairage de toute la zone est compromis. C'est une urgence de sécurité publique.

#### 40–79 % lampadaires hors ligne (+40)
Une défaillance partielle significative : une majorité des lampadaires est hors ligne. La visibilité de la zone est réduite de moitié ou plus. Intervention rapide nécessaire.

#### >0 % lampadaires hors ligne (+20)
Il y a des pannes dans la zone mais elles restent minoritaires. À traiter dans les délais normaux.

#### Alertes critiques (+min(30, nb × 10))
Chaque alerte critique dans la zone ajoute 10 points, plafonnée à 30. Cela évite qu'une zone avec de nombreuses alertes (mais peu de pannes) soit surévaluée.

#### Bons de travail ouverts (+10)
Des interventions sont déjà planifiées ou en cours dans cette zone. Cela signale une zone active où les ressources techniques sont déjà mobilisées.

---

### Tableau récapitulatif — Zone

| Critère | Points | Signification |
|---|---|---|
| ≥ 80 % hors ligne | +60 | Défaillance quasi-totale de la zone |
| ≥ 40 % hors ligne | +40 | Défaillance majeure |
| > 0 % hors ligne | +20 | Pannes ponctuelles |
| Alertes critiques (×10, max 30) | +0 à +30 | Risques actifs dans la zone |
| Bons de travail ouverts | +10 | Interventions en cours |

---

### Mapping score → priorité zone

| Score | Priorité | Action |
|---|---|---|
| ≥ 75 | CRITICAL | Mobilisation d'urgence, toute la zone |
| 50–74 | HIGH | Intervention planifiée sous 24h |
| 25–49 | MEDIUM | Inclure dans la prochaine tournée |
| < 25 | LOW | Surveillance normale |

---

### Exemple zone

```
Zone Médina :
  Total lampadaires : 80
  Hors ligne : 50 (62.5 %) → +40
  Alertes critiques : 4 → min(30, 4×10) = +40 (plafonné à 30)
  Bons de travail ouverts → +10

Score = 40 + 30 + 10 = 80 → CRITICAL
```
→ La Zone Médina est en état critique. Enquêter d'abord sur les LCUs de cette zone avant d'intervenir sur les lampadaires individuels.

---

## Pourquoi prioriser LCU et zone avant les lampadaires individuels ?

Une panne groupée (plusieurs lampadaires d'une même LCU ou zone en panne simultanément) a presque toujours une cause commune : LCU hors ligne, coupure d'alimentation secteur, problème réseau. Envoyer des techniciens sur chaque lampadaire individuellement avant d'avoir vérifié la LCU ou le réseau est inefficace et coûteux.

**Règle pratique :**
1. Score LCU CRITICAL → intervenir sur la LCU en premier
2. Score zone CRITICAL → vérifier l'alimentation et les LCUs de la zone
3. Seulement après → traiter les lampadaires individuels restants

---

## Limites et hypothèses

- Le score de zone suppose une délimitation géographique pertinente des zones dans la base de données. Des zones mal définies peuvent produire des scores trompeurs.
- Le score LCU dépend du `health_score` calculé séparément (vue `ai_lcu_health`). Ce score intermédiaire peut lui-même être basé sur des données simulées.
- En mode démonstrateur, les taux de pannes sont générés par le simulateur et ne reflètent pas un réseau réel.
- Le score de zone ne tient pas compte de l'importance stratégique des lampadaires (un axe principal vs. une ruelle). 

## Source technique

`smart-lighting-ai/app/recommendations/scoring.py`
Fonctions :
- `compute_lcu_risk_score(lcu_data) → int`
- `compute_zone_risk_score(zone_data) → int`
