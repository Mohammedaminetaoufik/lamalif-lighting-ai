---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: limites_hypotheses
source_code: multiple
audience: admin,technicien,ingenieur
---

# Limites et hypothèses des calculs

## Objectif de ce document

Ce document recense de manière honnête et exhaustive les limites, hypothèses et conditions d'utilisation de tous les calculs de la plateforme Lamalif Télégestion. Cette transparence est essentielle pour que l'opérateur interprète correctement les résultats affichés et ne prenne pas de décisions basées sur des valeurs incorrectement assimilées à des mesures précises.

---

## Limite 1 — Données simulées (mode démonstrateur)

**État actuel :** La télémétrie affichée dans la plateforme est générée par un service de simulation (`simulator.go`) et non par des capteurs physiques réels.

**Conséquence :** Les alertes, les scores de risque, les calculs énergétiques et les recommandations IA produits en mode démonstrateur sont **des démonstrations fonctionnelles**, pas des diagnostics opérationnels.

**Ce que cela change :** Les formules et les workflows sont corrects et représentatifs de ce qu'ils feront avec des données réelles. Les valeurs numériques (températures, consommations) ne correspondent pas à un réseau physique.

**Résolution :** Connecter l'adaptateur LCU (`HTTPLCUAdapter`) à des boîtiers LCU physiques pour recevoir de la télémétrie réelle.

---

## Limite 2 — Relation non linéaire entre dimming et consommation

**Hypothèse utilisée :** `Puissance_actuelle = Puissance_nominale × intensité / 100`

Cette formule suppose une relation **linéaire parfaite** entre le niveau de dimming (%) et la puissance consommée (W).

**Réalité terrain :** Cette relation n'est pas parfaitement linéaire pour tous les types de drivers :
- Les drivers DALI peuvent présenter des seuils de fonctionnement minimum
- Certains drivers consomment une puissance de veille non nulle à 0 %
- La relation peut être quasi-linéaire de 20 % à 100 % mais déviante en dessous de 20 %
- Le facteur de puissance (cos φ) change avec le niveau de charge

**Conséquence :** Les calculs d'économies et de coûts sont des estimations. La précision réelle dépend du type de driver installé.

**Résolution :** Mesurer la courbe de charge réelle de chaque type de driver installé et intégrer une table de correspondance intensité → puissance réelle.

---

## Limite 3 — Tarif kWh non configurable dans cette version

**Hypothèse utilisée :** Tarif = **1.20 DH/kWh** (valeur de référence)

**Réalité :** Le tarif électrique varie selon :
- Le type de contrat (Haute Tension, Moyenne Tension, Basse Tension)
- Les tranches horaires (heures pleines, heures creuses, pointe)
- Les conditions négociées avec l'opérateur (RADEEMA, ONEE, etc.)
- Les évolutions tarifaires annuelles

**Conséquence :** Les estimations de coût en DH peuvent être inexactes si le tarif réel est différent.

**Résolution :** Rendre le tarif configurable via la table `system_settings` ou un paramètre admin.

---

## Limite 4 — Facteur CO₂ non configurable dans cette version

**Hypothèse utilisée :** Facteur CO₂ = **0.638 kg CO₂/kWh** (mix énergétique marocain indicatif)

**Réalité :** Ce facteur varie selon :
- L'évolution du mix énergétique national (plus de renouvelables → facteur plus faible)
- La région (certaines zones sont alimentées par des sources renouvelables locales)
- L'heure (la composition du réseau change entre le jour et la nuit)
- Les publications annuelles de l'ONEE

**Conséquence :** Les estimations de CO₂ évité sont indicatives et doivent être mises à jour régulièrement.

**Résolution :** Configurer ce facteur via l'interface admin avec une date de mise à jour visible.

---

## Limite 5 — Seuils non calibrés sur données terrain

**État actuel :** Tous les seuils (75 °C, 30 lux, 70 lux, 1.30, 1.50, 6h, 24h, 48h) sont des valeurs de référence industrielles génériques.

**Risques :**
- Un seuil trop bas génère des fausses alarmes (alertes pour situations normales)
- Un seuil trop haut masque de vraies anomalies (pannes non détectées)

**Résolution :** Collecter 3 à 6 mois de données terrain réelles et analyser la distribution des valeurs pour calibrer les seuils sur la réalité du réseau.

---

## Limite 6 — Scores heuristiques, non des probabilités statistiques

**État actuel :** Les indices de causes probables (`06_causes_probables.md`) et les scores de risque sont calculés par des formules heuristiques déterministes.

**Ce que cela signifie :**
- Ces scores n'ont pas été entraînés sur des données historiques de pannes
- Ils ne sont pas des probabilités statistiques au sens mathématique
- Ils peuvent être incorrects dans des situations atypiques (acte de vandalisme, catastrophe naturelle)

**Ce que cela ne signifie pas :**
- Ils ne sont pas inutiles : ils orientent correctement le diagnostic dans les cas courants
- Ils sont prévisibles et auditables : on peut toujours expliquer pourquoi un score est élevé

**Résolution :** Après 12 à 24 mois de données terrain réelles avec des incidents documentés, entraîner un modèle statistique sur les données historiques pour remplacer les heuristiques.

---

## Limite 7 — Facteur de puissance non intégré

**État actuel :** Les calculs utilisent la puissance apparente (W) sans correction par le facteur de puissance (cos φ).

**Réalité terrain :** Les drivers LED ont en général un facteur de puissance de 0.90 à 0.99. Une correction par cos φ améliorerait la précision des calculs d'énergie active.

**Formule corrigée (future) :**
```
Puissance_active (W) = Puissance_apparente (VA) × cos φ
```

---

## Limite 8 — Calculs d'économies sur profils horaires basés sur hypothèses fixes

**Hypothèses hardcodées :**
- Réduction par dimming nuit creuse : **45 %** de la puissance
- Durée de nuit creuse : **5 heures**
- Réduction par dimming variable : **30 %** de la puissance
- Durée d'application : **8 heures**

Ces valeurs sont des approximations raisonnables pour une estimation rapide. Elles ne remplacent pas un calcul basé sur des profils horaires réels.

---

## Limite 9 — Intervalle de mesure fixe à 5 minutes

**Hypothèse :** Toutes les formules d'énergie supposent un intervalle de 5 minutes entre les mesures.

**Réalité :** Si l'équipement terrain envoie des mesures toutes les 1, 10 ou 15 minutes, les formules d'énergie produiront des résultats incorrects sans adaptation.

---

## Limite 10 — Score réseau mis en cache 5 minutes

**Impact :** Le score réseau peut être décalé de 5 minutes par rapport à l'état réel. En cas d'incident massif (coupure secteur soudaine), le score peut rester "normal" pendant 5 minutes avant d'être recalculé.

---

## Récapitulatif des limites

| Limite | Impact | Résolution recommandée |
|---|---|---|
| Données simulées | Élevé | Connecter LCU physique |
| Dimming non linéaire | Modéré | Calibration par type de driver |
| Tarif kWh fixe | Modéré | Configurer dans system_settings |
| Facteur CO₂ fixe | Faible | Configurer dans system_settings |
| Seuils non calibrés | Modéré | 3–6 mois de données terrain |
| Scores heuristiques | Faible-Modéré | Données historiques + ML (12–24 mois) |
| Facteur de puissance absent | Faible | Intégrer cos φ dans calcul énergie |
| Hypothèses économies profils | Faible | Profils horaires réels en production |
| Intervalle fixe 5 min | Faible | Adapter si intervalle différent |
| Cache 5 min score réseau | Très faible | Acceptable en production |

---

## Ce que le LLM doit faire avec ces limites

Quand le LLM explique un résultat calculé, il doit :
1. Citer la formule utilisée
2. Mentionner si le résultat est une estimation
3. Indiquer si les données sont simulées
4. Signaler si un tarif ou facteur est configurable
5. Ne jamais présenter une estimation comme une mesure précise

**Exemple de formulation correcte :**
> "Le coût estimé est de 71 DH, calculé avec un tarif de 1,20 DH/kWh. Cette valeur est une estimation — le tarif doit être configuré selon votre contrat électrique réel."

**Exemple de formulation incorrecte (à éviter) :**
> "Le coût exact est 71 DH."

## Source technique

Toutes les formules documentées dans ce corpus `rag_docs/metier/calculs/`.
