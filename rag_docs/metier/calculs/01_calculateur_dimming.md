---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: calculateur_dimming
source_code: smart-lighting-web/backend/internal/services/calculator.go
audience: admin,technicien,ingenieur
---

# Calculateur intelligent de dimming

## Résumé — Comment fonctionne le dimming automatique

Le dimming automatique fonctionne via un **moteur de décision séquentiel à 7 règles**. La première règle dont la condition est vraie est appliquée ; les suivantes sont ignorées. Il n'y a pas d'équation unique — c'est une logique conditionnelle ordonnée par priorité.

**Les 7 règles du calculateur de dimming :**

| Priorité | Condition | Intensité recommandée | Confiance |
|---|---|---|---|
| 1 | État = maintenance | **0 %** | 1.00 |
| 2 | Température driver > 75 °C | **min(intensité actuelle, 50 %)** | 0.95 |
| 3 | Présence détectée ET luminosité < 30 lux | **90 %** | 0.90 |
| 4 | Pas de présence ET heure entre 0h et 5h | **30 %** | 0.85 |
| 5 | Pas de présence ET luminosité < 30 lux | **50 %** | 0.80 |
| 6 | Luminosité ambiante > 70 lux (jour) | **20 %** | 0.85 |
| 7 | Aucune règle ne correspond (défaut) | **60 %** | 0.70 |

**Formule de la règle 2 (protection thermique) :**
```
intensite_cible = min(intensite_courante, 50)
```

**Variables d'entrée :** état du lampadaire, température driver (°C), présence (booléen), luminosité ambiante (lux), heure système (0–23).

**Seuils clés :** 75 °C (protection thermique), 30 lux (seuil obscurité), 70 lux (seuil jour), 0h–5h (nuit creuse).

**Règle absolue :** la recommandation n'est jamais appliquée automatiquement — une validation humaine est obligatoire avant envoi à la LCU.

---

## Objectif métier

Le calculateur de dimming détermine automatiquement le niveau d'intensité lumineuse optimal pour chaque lampadaire en fonction de son environnement et de son état. Son objectif est de réduire la consommation électrique sans compromettre la sécurité des usagers, tout en protégeant l'équipement contre les conditions dangereuses.

Ce calcul est **exécuté par le moteur Go** (`calculator.go`). Le LLM explique les décisions prises, il ne les recrée pas.

---

## Moteur de décision séquentiel

Le calculateur applique les règles **dans l'ordre** : la première règle dont la condition est vraie est appliquée, les suivantes sont ignorées. Cette approche garantit la prévisibilité et l'explicabilité totale de chaque décision.

---

## Règle 1 — Mode maintenance

**Condition :** `etat == "maintenance"`

**Résultat :**
- Intensité = **0 %**
- Confiance = **1.00** (certitude absolue)

**Pourquoi :** Un lampadaire en mode maintenance est physiquement inaccessible ou en cours d'intervention. Allumer le lampadaire pendant une intervention exposerait le technicien à un risque électrique. La décision est certaine à 100 % car elle repose sur un état explicitement défini.

**Variables :**
- `etat` : état logistique du lampadaire (`online`, `offline`, `maintenance`)

---

## Règle 2 — Protection thermique

**Condition :** `temperature > 75 °C`

**Résultat :**
- Intensité = `min(intensite_actuelle, 50 %)`
- Confiance = **0.95**

**Formule :**
```
intensite_cible = min(intensite_courante, 50)
```

**Pourquoi :** Une température driver supérieure à 75 °C indique un risque de surchauffe. Réduire l'intensité à 50 % maximum réduit la dissipation thermique et protège le driver LED d'un emballement thermique pouvant conduire à une panne définitive. La confiance est de 0.95 car la mesure capteur peut présenter une légère imprécision.

**Variables :**
- `temperature` : température du driver LED (°C), issue de la dernière mesure de télémétrie
- `intensite_actuelle` : niveau d'intensité courant du lampadaire (%)

**Exemple :**
Un lampadaire tourne à 80 % d'intensité. Sa température est 78 °C.
Le calculateur impose : `min(80, 50) = 50 %`.

---

## Règle 3 — Présence détectée en obscurité

**Condition :** `presence == true AND luminosite < 30 lux`

**Résultat :**
- Intensité = **90 %**
- Confiance = **0.90**

**Pourquoi :** Quand un capteur de présence détecte une personne ou un véhicule dans des conditions sombres (moins de 30 lux), la sécurité est prioritaire. L'intensité monte à 90 % pour assurer un éclairage suffisant. La confiance est de 0.90 car les capteurs de présence peuvent produire de faux positifs.

**Variables :**
- `presence` : signal capteur de présence (booléen)
- `luminosite` : luminosité ambiante mesurée en lux (0–100+)

---

## Règle 4 — Nuit creuse sans présence

**Condition :** `presence == false AND heure ∈ [0h, 5h[`

**Résultat :**
- Intensité = **30 %**
- Confiance = **0.85**

**Pourquoi :** Entre minuit et 5h du matin, l'activité humaine est minimale. En l'absence de présence détectée, réduire l'intensité à 30 % permet d'économiser jusqu'à 70 % de la puissance nominale pendant les heures les moins actives de la nuit. La confiance de 0.85 reflète l'incertitude sur l'absence totale d'activité.

**Variables :**
- `presence` : signal capteur de présence
- `heure` : heure courante (0–23), extraite de l'horloge système

---

## Règle 5 — Obscurité sans présence (hors nuit creuse)

**Condition :** `presence == false AND luminosite < 30 lux`

**Résultat :**
- Intensité = **50 %**
- Confiance = **0.80**

**Pourquoi :** En l'absence de présence détectée mais dans des conditions sombres, il est prudent de maintenir une intensité modérée (50 %) pour permettre la détection visuelle de l'environnement par des passants potentiels non détectés. La confiance plus faible (0.80) reflète le fait que les capteurs de présence ne couvrent pas toujours 100 % de la zone d'éclairage.

---

## Règle 6 — Forte luminosité ambiante (jour)

**Condition :** `luminosite > 70 lux`

**Résultat :**
- Intensité = **20 %**
- Confiance = **0.85**

**Pourquoi :** Quand la lumière naturelle dépasse 70 lux, l'éclairage artificiel devient superflu pour la sécurité des usagers. Maintenir une intensité minimale de 20 % assure la visibilité du lampadaire sans gaspiller d'énergie. Cette règle détecte notamment les cas de « brûlage diurne » (lampadaire allumé en plein jour).

**Variables :**
- `luminosite` : luminosité ambiante mesurée (lux)

---

## Règle 7 — Cas par défaut

**Condition :** aucune règle précédente ne correspond

**Résultat :**
- Intensité = **60 %**
- Confiance = **0.70**

**Pourquoi :** En l'absence de données suffisantes (capteur absent, données périmées, situation non couverte), le calculateur adopte une position prudente à 60 % — suffisant pour l'éclairage standard sans surconsommation. La confiance de 0.70 signale que cette décision est moins fiable et qu'une vérification terrain est recommandée.

---

## Tableau récapitulatif

| Priorité | Condition | Intensité | Confiance | Raison |
|---|---|---|---|---|
| 1 | Maintenance | 0 % | 1.00 | Sécurité technicien |
| 2 | Température > 75 °C | min(actuelle, 50 %) | 0.95 | Protection driver |
| 3 | Présence + Luminosité < 30 lux | 90 % | 0.90 | Sécurité usagers |
| 4 | Pas présence + Heure 0–5h | 30 % | 0.85 | Économie nuit creuse |
| 5 | Pas présence + Luminosité < 30 lux | 50 % | 0.80 | Économie modérée |
| 6 | Luminosité > 70 lux | 20 % | 0.85 | Lumière naturelle |
| 7 | Défaut | 60 % | 0.70 | Position de prudence |

---

## Interprétation de la confiance

La confiance mesure la fiabilité de la décision :
- **0.95–1.00** : Décision certaine, basée sur un état ou seuil physique clair
- **0.80–0.94** : Décision fiable, légère incertitude sur la mesure capteur
- **0.70–0.79** : Décision par défaut, supervision humaine recommandée

---

## Pourquoi ce système est explicable (non boîte noire)

Contrairement à un modèle de machine learning, chaque décision du calculateur peut être auditée et expliquée :
1. La règle déclenchée est enregistrée dans `calculator_decisions`
2. Les valeurs d'entrée ayant conduit à la décision sont tracées
3. La confiance indique la certitude de la décision
4. Aucun paramètre caché, aucun poids neuronal : seulement des seuils et des conditions

---

## Exemple complet

**Lampadaire LP-044, 23h30 :**
- etat = `online`
- temperature = 72 °C (règle 2 non déclenchée)
- presence = false
- luminosite = 8 lux
- heure = 23

→ Règle 1 : non (online)
→ Règle 2 : non (72 < 75)
→ Règle 3 : non (presence = false)
→ Règle 4 : non (heure = 23, pas dans [0,5))
→ Règle 5 : OUI (presence = false ET luminosite = 8 < 30)

**Décision : intensité = 50 %, confiance = 0.80**

---

## Limites et hypothèses

- Les seuils (75 °C, 30 lux, 70 lux, 30 %) sont des valeurs initiales à calibrer selon le type de luminaire, la zone et le contrat client.
- La détection de présence dépend de la qualité et de la portée du capteur installé.
- L'heure utilisée est l'heure du serveur — à valider avec le fuseau horaire local.
- En absence de télémétrie récente, les mesures de température et luminosité peuvent être périmées.

## Source technique

`smart-lighting-web/backend/internal/services/calculator.go`
Fonction : `RunCalculator(lamp, telemetry, hour) → DecisionResult`
