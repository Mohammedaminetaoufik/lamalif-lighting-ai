# Questions de validation RAG — Calculs Lamalif Télégestion

Ce fichier sert de référence pour tester que le système RAG récupère les bons documents et que le LLM produit des réponses structurées, précises et honnêtes pour les questions liées aux calculs.

## Comment utiliser ce fichier

Pour chaque question :
1. Envoyer la question via `POST /ai/query`
2. Vérifier que `response.rag.sources` contient le(s) document(s) attendu(s)
3. Vérifier que la réponse contient la formule
4. Vérifier que la réponse contient l'interprétation métier
5. Vérifier que la réponse mentionne les limites si le calcul est une estimation
6. Vérifier que la réponse n'invente pas de données

---

## Q1 — Coût énergétique

**Question :** Comment le coût énergétique est calculé ?

**Documents RAG attendus :**
- `04_calculs_energetiques` (primaire)
- `12_limites_hypotheses_calculs` (secondaire)

**La réponse doit contenir :**
- [ ] La formule : `Coût = Consommation (kWh) × Tarif (DH/kWh)`
- [ ] Le tarif de référence : 1,20 DH/kWh
- [ ] La mention que le tarif est configurable
- [ ] Un exemple numérique

**La réponse ne doit pas :**
- [ ] Inventer une consommation si aucune donnée n'est fournie
- [ ] Présenter le coût comme une valeur exacte sans mentionner les limites

---

## Q2 — Économies estimées

**Question :** Pourquoi les économies d'énergie sont-elles des estimations ?

**Documents RAG attendus :**
- `12_limites_hypotheses_calculs` (primaire)
- `04_calculs_energetiques` (secondaire)

**La réponse doit contenir :**
- [ ] L'hypothèse de linéarité du dimming et ses limites
- [ ] La mention du tarif configurable
- [ ] La mention du facteur de puissance (cos φ)
- [ ] La mention des données simulées (mode démonstrateur)

---

## Q3 — CO₂ évité

**Question :** Comment le CO₂ évité est calculé ?

**Documents RAG attendus :**
- `04_calculs_energetiques` (primaire)

**La réponse doit contenir :**
- [ ] La formule : `CO₂ = Énergie_économisée × Facteur_CO₂`
- [ ] Le facteur de 0,638 kg CO₂/kWh (indicatif, Maroc)
- [ ] La mention que ce facteur doit être mis à jour
- [ ] Un exemple numérique

---

## Q4 — Alerte température critique

**Question :** Pourquoi une alerte température est-elle critique ?

**Documents RAG attendus :**
- `02_regles_alertes_automatiques` (primaire)
- `11_seuils_metier` (secondaire)

**La réponse doit contenir :**
- [ ] Le seuil de déclenchement : 75 °C
- [ ] Le seuil de résolution : 65 °C
- [ ] L'explication de l'hystérésis
- [ ] L'impact sur le calculateur de dimming (limite à 50 %)
- [ ] La sévérité CRITICAL et sa signification

---

## Q5 — Score réseau

**Question :** Comment le score réseau est calculé ?

**Documents RAG attendus :**
- `05_score_reseau_decision_center` (primaire)

**La réponse doit contenir :**
- [ ] La formule complète (100 − pénalités)
- [ ] Les 3 pénalités (lampadaires, alertes, LCUs)
- [ ] La classification (≥71 normal, 41–70 warning, ≤40 critical)
- [ ] Un exemple numérique

---

## Q6 — Priorité LCU

**Question :** Pourquoi la LCU KECH est-elle prioritaire ?

**Documents RAG attendus :**
- `09_scores_risque_lcu_zone` (primaire)
- `06_causes_probables` (secondaire)

**La réponse doit contenir :**
- [ ] Le score de risque LCU et les critères
- [ ] La règle "LCU avant lampadaires"
- [ ] Les actions concrètes à effectuer

---

## Q7 — Score heuristique vs probabilité statistique

**Question :** Quelle est la différence entre un indice de cause probable et une probabilité statistique ?

**Documents RAG attendus :**
- `06_causes_probables` (primaire)
- `12_limites_hypotheses_calculs` (secondaire)

**La réponse doit contenir :**
- [ ] La distinction claire : heuristique déterministe vs modèle statistique entraîné
- [ ] L'absence de données historiques d'entraînement
- [ ] L'utilité malgré cette limite
- [ ] La mention "indice de cause probable" et non "probabilité"

**La réponse ne doit pas :**
- [ ] Affirmer que les indices sont des probabilités statistiques
- [ ] Affirmer que le système utilise du machine learning

---

## Q8 — Score de risque lampadaire

**Question :** Comment le score de risque d'un lampadaire est calculé ?

**Documents RAG attendus :**
- `07_scores_risque_lampadaire` (primaire)
- `10_priorites_recommandations` (secondaire)

**La réponse doit contenir :**
- [ ] Les 8 critères avec leurs points
- [ ] La formule de base (score commence à 0)
- [ ] Le mapping score → priorité
- [ ] Un exemple numérique

---

## Q9 — Zone critique

**Question :** Pourquoi une zone devient-elle critique ?

**Documents RAG attendus :**
- `09_scores_risque_lcu_zone` (primaire)

**La réponse doit contenir :**
- [ ] Les seuils de taux de panne (80 %, 40 %, >0 %)
- [ ] Le score et le mapping vers CRITICAL
- [ ] L'explication que c'est une panne groupée
- [ ] La recommandation d'investiguer LCU/alimentation avant les lampadaires

---

## Q10 — Dimming et consommation

**Question :** Pourquoi le dimming réduit-il la consommation électrique ?

**Documents RAG attendus :**
- `01_calculateur_dimming` (primaire)
- `04_calculs_energetiques` (secondaire)
- `12_limites_hypotheses_calculs` (secondaire)

**La réponse doit contenir :**
- [ ] L'explication du lien intensité → puissance
- [ ] La formule : `P_actuelle = P_nominale × intensité/100`
- [ ] L'hypothèse de linéarité et ses limites
- [ ] Un exemple numérique (lampadaire 100 W à 50 % = 50 W)

---

## Q11 — Calculateur de dimming

**Question :** Quelles sont les règles du calculateur de dimming ?

**Documents RAG attendus :**
- `01_calculateur_dimming` (primaire)

**La réponse doit contenir :**
- [ ] Les 7 règles dans l'ordre de priorité
- [ ] Le principe "première règle satisfaite"
- [ ] Les valeurs d'intensité pour chaque règle
- [ ] La valeur de confiance

---

## Q12 — Seuils métier

**Question :** Quels sont les seuils de température utilisés dans la plateforme ?

**Documents RAG attendus :**
- `11_seuils_metier` (primaire)
- `02_regles_alertes_automatiques` (secondaire)

**La réponse doit contenir :**
- [ ] Le tableau complet des seuils thermiques
- [ ] La distinction entre seuil alerte (75 °C) et seuil scoring (80 °C)
- [ ] La mention que ces seuils doivent être calibrés

---

## Critères de validation globaux

Pour **toutes** les réponses :

- [ ] La réponse est structurée (sections avec ###)
- [ ] Elle cite la formule si disponible dans le RAG
- [ ] Elle mentionne les limites si le calcul est une estimation
- [ ] Elle n'invente pas de chiffres absents des données
- [ ] Elle ne présente pas un score heuristique comme une probabilité statistique
- [ ] Elle ne dit pas "le système utilise du machine learning" pour les calculs rule-based
- [ ] Elle donne une action recommandée quand c'est pertinent
- [ ] Elle mentionne si les données sont simulées (mode démonstrateur)
- [ ] Elle indique qu'un tarif ou facteur est configurable quand c'est le cas
