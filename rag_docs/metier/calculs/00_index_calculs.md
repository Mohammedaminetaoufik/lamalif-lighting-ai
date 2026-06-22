---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: index_global
source_code: multiple
audience: admin,technicien,ingenieur
---

# Index des calculs — Lamalif Télégestion

Ce document est le point d'entrée de la documentation des calculs de la plateforme Lamalif Télégestion. Il recense les 14 familles de calculs, leur rôle, et la différence fondamentale entre le code qui exécute les calculs, la documentation RAG qui les explique, et le LLM qui rédige les réponses.

---

## Principe fondamental

**Le moteur de calcul est déterministe et explicable. Le LLM ne décide pas seul et n'exécute pas les calculs critiques. Il utilise les résultats calculés par le système et la documentation RAG pour fournir une explication claire à l'utilisateur.**

| Couche | Rôle | Exemples |
|---|---|---|
| **Code (Go / Python)** | Exécuter les calculs, appliquer les règles, écrire en base | Calculator.go, alert_rules.go, scoring.py |
| **Documentation RAG** | Expliquer les formules, les seuils, les interprétations | Ce dossier rag_docs/metier/calculs/ |
| **LLM (Groq / OpenAI)** | Rédiger une explication claire à partir des résultats fournis | generate_professional_answer() |

Le LLM ne recalcule jamais. Il reçoit des résultats déjà calculés et les explique en language naturel avec l'appui de ce corpus documentaire.

---

## Familles de calculs (résumé)

### 1. Dimming intelligent
**Fichier :** `01_calculateur_dimming.md`
Moteur de décision séquentiel à 7 règles qui détermine l'intensité lumineuse optimale selon l'état du lampadaire, la température, la présence détectée, l'heure et la luminosité ambiante.

### 2. Alertes automatiques
**Fichier :** `02_regles_alertes_automatiques.md`
4 règles de déclenchement automatique basées sur des seuils physiques (température, humidité, surconsommation). Chaque alerte a un seuil de déclenchement distinct du seuil de résolution (hystérésis).

### 3. Simulateur de télémétrie
**Fichier :** `03_simulateur_telemetrie.md`
7 scénarios de simulation générant des mesures électriques cohérentes (tension, courant, puissance, énergie, température) pour tester les workflows avant connexion matérielle réelle.

### 4. Calculs énergétiques
**Fichier :** `04_calculs_energetiques.md`
12 formules pour calculer l'énergie consommée (kWh), les économies réalisées par le dimming, le coût estimé en DH et le CO₂ évité. Ces calculs sont des **estimations** basées sur les données disponibles.

### 5. Score réseau IA
**Fichier :** `05_score_reseau_decision_center.md`
Score composite 0–100 pénalisant les lampadaires hors ligne (−60 max), les alertes critiques (−20 max) et les LCUs hors ligne (−20 max). Donne une vision instantanée de la santé globale du réseau.

### 6. Causes probables
**Fichier :** `06_causes_probables.md`
4 indices heuristiques (0.0–0.95) orientant le diagnostic vers les causes les plus vraisemblables. Ce ne sont pas des probabilités statistiques : ce sont des guides d'investigation.

### 7. Scores de risque lampadaire
**Fichier :** `07_scores_risque_lampadaire.md`
Score de risque 0–100 agrégeant l'état, les alertes, la température driver, l'âge du bon de travail et la qualité de mise en service. Aide à prioriser les interventions terrain.

### 8. Scores de maintenabilité et communication
**Fichier :** `08_scores_maintenabilite_communication.md`
Deux scores complémentaires : la maintenabilité mesure la qualité des données du lampadaire (GPS, LCU, zone), la communication mesure la qualité du lien réseau (last_seen_at, signal, LCU).

### 9. Scores de risque LCU et zone
**Fichier :** `09_scores_risque_lcu_zone.md`
Scores pour évaluer le risque d'une passerelle LCU et d'une zone géographique. Une LCU critique impacte tous ses lampadaires. Un score de zone élevé signale une panne groupée à traiter en priorité.

### 10. Priorités des recommandations
**Fichier :** `10_priorites_recommandations.md`
Mapping du score de risque technique (0–100) vers une priorité métier (low / medium / high / critical). Ce mapping est la passerelle entre le calcul et l'action.

### 11. Seuils métier globaux
**Fichier :** `11_seuils_metier.md`
Catalogue de toutes les constantes et seuils utilisés dans les calculs : températures, délais, taux de pannes, intensité dimming. Ces seuils doivent devenir configurables dans une version entreprise.

### 12. Limites et hypothèses
**Fichier :** `12_limites_hypotheses_calculs.md`
Document critique expliquant ce que les calculs ne prouvent pas encore : données simulées, calibration terrain manquante, tarifs configurables, linéarité du dimming à valider.

### 13. Exemples d'explication IA
**Fichier :** `13_exemples_explication_ia.md`
Paires question/réponse illustrant comment le LLM doit expliquer les résultats calculés de manière structurée, avec formule, interprétation et limites.

---

## Résumé des calculs par domaine

| Domaine | Calculs | Fichier |
|---|---|---|
| Dimming | 7 règles séquentielles | 01 |
| Alertes | 4 règles + hystérésis | 02 |
| Simulation | 7 scénarios × 5 formules électriques | 03 |
| Énergie | kWh, coût DH, économies, CO₂ | 04 |
| Score réseau | 1 score composite, 3 pénalités | 05 |
| Causes probables | 4 indices heuristiques | 06 |
| Risque lampadaire | 1 score, 8 critères | 07 |
| Maintenabilité + Communication | 2 scores | 08 |
| Risque LCU + Zone | 2 scores | 09 |
| Priorité | 1 mapping score→niveau | 10 |
| Seuils globaux | ~15 constantes | 11 |

---

## Ce que le LLM est autorisé à faire

- Citer une formule depuis ce corpus documentaire
- Expliquer en langage naturel un résultat déjà calculé par l'API
- Indiquer les limites d'un calcul (estimation, simulation, calibration manquante)
- Orienter vers une action humaine

## Ce que le LLM ne doit jamais faire

- Recalculer un score ou une énergie par lui-même sans données fournies
- Inventer un tarif kWh, un facteur CO₂ ou un seuil
- Présenter un indice heuristique comme une probabilité statistique entraînée
- Affirmer que le système utilise du machine learning si le calcul est déterministe
- Déclencher automatiquement une action (dimming, coupure, intervention)
