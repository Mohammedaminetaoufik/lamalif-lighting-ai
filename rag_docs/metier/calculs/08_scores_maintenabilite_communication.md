---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: maintenabilite_communication
source_code: smart-lighting-ai/app/recommendations/scoring.py
audience: admin,technicien,ingenieur
---

# Scores de maintenabilité et de santé communication

## Objectif métier

Ces deux scores évaluent des dimensions complémentaires de la qualité opérationnelle d'un lampadaire :

- **Score de maintenabilité** : mesure si les données du lampadaire sont suffisamment complètes pour permettre un diagnostic et une maintenance efficaces. Un score faible signale un lampadaire "mal documenté" dans le système.

- **Score de santé communication** : mesure la qualité du lien de communication entre le lampadaire et sa LCU. Un score faible peut indiquer une panne réseau, une LCU défaillante, ou un problème de signal radio.

Ces deux scores sont calculés par `scoring.py` et servent à enrichir les recommandations de l'IA.

---

## Score de maintenabilité

### Formule
```
score = 100

−15  si pas de coordonnées GPS
−20  si pas de LCU associée
−15  si dernière télémétrie > 6h
−20  si bon de travail ouvert depuis > 48h
−10  si pas de zone assignée
−10  si non mis en service (commissioning_status ≠ "commissioned")

score = max(0, score)
```

### Détail des critères

#### GPS manquant (−15)
Un lampadaire sans coordonnées GPS est introuvable sur la carte interactive. Le technicien ne peut pas le localiser physiquement depuis l'application mobile. Il est impossible de planifier une intervention géolocalisée, de visualiser sa position relative à la LCU, ou d'optimiser les tournées d'intervention.

#### LCU non associée (−20)
Un lampadaire non rattaché à une LCU est complètement isolé du système de supervision. Aucune commande de dimming ne peut lui être envoyée. Aucune télémétrie ne peut être collectée automatiquement. C'est la pénalité la plus forte car elle rend impossible la supervision à distance.

#### Télémétrie obsolète > 6h (−15)
Sans mesures récentes, le diagnostic à distance est impossible. L'état affiché (température, puissance) peut ne pas refléter la réalité terrain. Ce critère indique souvent un problème de communication, de LCU, ou un lampadaire éteint.

#### Bon de travail ouvert > 48h (−20)
Un incident non résolu depuis plus de 48 heures signifie soit que la panne est complexe, soit que le workflow de maintenance est bloqué (ressource manquante, pièce en attente). Ce critère a le même poids que l'absence de LCU car il indique une situation anormale persistante.

#### Zone non assignée (−10)
Un lampadaire sans zone n'est pas visible dans les analyses par zone, ni filtrable dans les rapports. Il est "invisible" du point de vue de la supervision territoriale.

#### Non mis en service (−10)
Un lampadaire dont le commissioning n'est pas finalisé a un statut opérationnel incertain. Les paramètres configurés peuvent ne pas avoir été validés par un test physique.

---

### Tableau récapitulatif — maintenabilité

| Critère | Pénalité | Impact |
|---|---|---|
| Pas de GPS | −15 | Inlocalisable sur carte |
| Pas de LCU | −20 | Supervision impossible |
| Télémétrie > 6h | −15 | Diagnostic à distance impossible |
| WO ouvert > 48h | −20 | Incident bloqué |
| Pas de zone | −10 | Invisible dans les analyses |
| Non mis en service | −10 | Statut incertain |

---

### Interprétation du score de maintenabilité

| Score | Interprétation |
|---|---|
| 85–100 | Lampadaire bien documenté, maintenance facile |
| 60–84 | Quelques données manquantes, maintenance possible |
| 40–59 | Données partielles, maintenance difficile |
| < 40 | Lampadaire mal documenté, intervention compliquée |

---

## Score de santé communication

### Formule
```
score = 100

−30  si non vu depuis > 24h (last_seen_at > 24h)
−15  si non vu depuis 6–24h
−40  si LCU associée hors ligne
−20  si LCU état inconnu
−25  si signal < 30 dBm
−10  si 30 dBm ≤ signal < 60 dBm

score = max(0, score)
```

### Détail des critères

#### Non vu depuis > 24h (−30)
La donnée `last_seen_at` indique la dernière fois que le lampadaire a communiqué. Au-delà de 24h, on considère que la communication est sévèrement dégradée ou rompue. Ce n'est pas forcément une panne physique — la LCU peut être hors ligne.

#### Non vu depuis 6–24h (−15)
Zone d'alerte intermédiaire. La communication est présente mais dégradée. Peut indiquer un problème radio intermittent ou une LCU redémarrée récemment.

#### LCU hors ligne (−40)
C'est la pénalité la plus forte : si la LCU est hors ligne, tous ses lampadaires perdent automatiquement leur communication, quelle que soit la qualité de leur signal radio individuel. Cette pénalité n'est pas cumulable avec "LCU état inconnu".

#### LCU état inconnu (−20)
L'état de la LCU n'a pas pu être déterminé (aucune mesure récente). Moins pénalisant qu'une LCU clairement hors ligne car il peut s'agir d'une absence de données plutôt que d'une panne confirmée.

#### Signal < 30 dBm (−25)
Un signal inférieur à 30 dBm est très faible pour une communication radio. Le risque de perte de paquets et de déconnexions est élevé. Cause possible : obstacle physique, distance excessive à la LCU, interférence.

#### Signal 30–59 dBm (−10)
Signal modéré, acceptable mais à surveiller. Une légère dégradation (travaux, déplacement d'obstacle) pourrait faire passer sous le seuil critique.

---

### Tableau récapitulatif — communication

| Critère | Pénalité | Signal d'alerte |
|---|---|---|
| Non vu > 24h | −30 | Panne communication probable |
| LCU hors ligne | −40 | Perte supervision complète |
| Signal < 30 dBm | −25 | Signal très faible |
| LCU état inconnu | −20 | Données insuffisantes |
| Non vu 6–24h | −15 | Communication dégradée |
| Signal 30–59 dBm | −10 | Signal modéré |

---

### Interprétation du score de santé communication

| Score | Interprétation |
|---|---|
| 80–100 | Communication excellente |
| 50–79 | Communication acceptable, surveillance recommandée |
| 20–49 | Communication dégradée, investigation requise |
| < 20 | Communication sévèrement compromise |

---

## Utilisation combinée des deux scores

Ces deux scores sont complémentaires et permettent de distinguer différents types de problèmes :

| Maintenabilité | Communication | Diagnostic probable |
|---|---|---|
| Élevée | Élevée | Lampadaire sain et bien documenté |
| Faible | Élevée | Données à compléter (GPS, LCU, zone) — pas de panne |
| Élevée | Faible | Problème réseau ou LCU — lampadaire documenté mais injoignable |
| Faible | Faible | Lampadaire problématique à tous niveaux — priorité d'investigation |

---

## Utilité pour le technicien terrain

- **Score maintenabilité faible** : Le technicien doit compléter les données (GPS, association LCU, zone) lors de sa visite.
- **Score communication faible + LCU hors ligne** : Avant d'intervenir sur les lampadaires individuels, il faut d'abord diagnostiquer la LCU.
- **Score communication faible + signal < 30 dBm** : Vérifier l'obstacle entre le lampadaire et la LCU, envisager un répéteur radio.

---

## Limites et hypothèses

- Le score de maintenabilité pénalise les données absentes mais ne peut pas savoir si elles sont absentes volontairement (lampadaire temporairement hors service, lampadaire en transit).
- Le score de communication dépend de `last_seen_at` qui peut rester à une ancienne valeur si le système n'a pas reçu de nouvelles mesures.
- En mode simulateur, ces scores sont calculés sur des données artificielles. Les seuils de signal dBm peuvent ne pas correspondre à la réalité physique du site.
- Les pénalités ne sont pas cumulatives à l'infini : le score est borné à 0. Un lampadaire avec toutes les pénalités maximum obtient 100 - 40 - 30 - 25 - 20 = 0 (pas négatif).

## Source technique

`smart-lighting-ai/app/recommendations/scoring.py`
Fonctions :
- `compute_lampadaire_maintainability_score(lamp_data) → int`
- `compute_communication_health_score(lamp_data) → int`
