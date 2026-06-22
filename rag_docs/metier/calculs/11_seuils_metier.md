---
document_type: calcul_metier
domain: smart_lighting
project: lamalif_telegestion
language: fr
version: 1.0
module: seuils_metier
source_code: smart-lighting-ai/app/recommendations/utils.py,smart-lighting-web/backend/internal/services/alert_rules.go,smart-lighting-web/backend/internal/services/calculator.go
audience: admin,technicien,ingenieur
---

# Seuils métier globaux

## Objectif métier

Les seuils métier sont les valeurs de référence utilisées dans tous les calculs de la plateforme pour décider si une situation est normale, dégradée ou critique. Ce document en est le catalogue complet. Ces seuils doivent devenir configurables dans une version entreprise pour s'adapter aux spécificités de chaque client, zone ou type d'équipement.

---

## Seuils de télémétrie et communication

| Constante | Valeur | Module | Signification |
|---|---|---|---|
| `TELEMETRY_STALE_HOURS` | **6 h** | scoring.py | Délai après lequel la télémétrie est considérée périmée |
| Seuil non vu — avertissement | **6 h** | communication score | Début de dégradation de la communication |
| Seuil non vu — critique | **24 h** | communication score | Communication sévèrement compromise |

### Justification des 6 heures
Les lampadaires transmettent en théorie toutes les 5 minutes. Si aucune mesure n'est reçue depuis 6 heures (72 mesures manquantes), le problème est systématique, pas accidentel. Ce seuil peut être réduit à 1 heure dans une configuration temps réel stricte.

---

## Seuils des bons de travail

| Constante | Valeur | Module | Signification |
|---|---|---|---|
| `WO_CRITICAL_HOURS` | **24 h** | scoring.py | Bon de travail critique non résolu en 24h |
| `WO_OLD_HOURS` | **48 h** | scoring.py | Bon de travail considéré "ancien" non résolu en 48h |

### Justification
- 24h : Une urgence terrain non traitée en 24h signale un problème de workflow ou de disponibilité.
- 48h : Délai maximum acceptable pour une intervention non urgente. Au-delà, le risque de dégradation augmente.

---

## Seuils de température driver

| Constante | Valeur | Module | Signification |
|---|---|---|---|
| `DRIVER_TEMP_HIGH` | **70 °C** | scoring.py | Zone de surveillance renforcée |
| `DRIVER_TEMP_CRITICAL` | **80 °C** | scoring.py | Risque élevé pour la durée de vie |
| Seuil alerte CRITICAL | **75 °C** | alert_rules.go | Déclenchement de l'alerte température |
| Seuil résolution alerte | **65 °C** | alert_rules.go | Résolution de l'alerte température |
| Seuil protection dimming | **75 °C** | calculator.go | Le calculateur limite l'intensité à 50 % |

### Récapitulatif thermique

```
< 65 °C    : Zone normale, pas d'action
65–69 °C   : Zone de surveillance (entre résolution et déclenchement alerte)
70–74 °C   : Score risque +15 pts, alerte non encore déclenchée
≥ 75 °C    : Alerte CRITICAL déclenchée + dimming limité à 50 %
≥ 80 °C    : Score risque +25 pts (risque très élevé pour le hardware)
```

### Justification
Les standards industriels LED (LM-80, TM-21) montrent que la durée de vie du driver est divisée par 2 environ tous les 10 °C au-delà de la température nominale (en général 60–65 °C). Les seuils de 70 et 80 °C sont des repères industriels courants.

---

## Seuils de consommation (alertes)

| Seuil | Valeur | Sévérité | Module |
|---|---|---|---|
| Consommation excessive — déclenchement | `P > P_nom × 1.30` | WARNING | alert_rules.go |
| Consommation excessive — résolution | `P < P_nom × 1.20` | WARNING | alert_rules.go |
| Consommation critique | `P > P_nom × 1.50` | CRITICAL | alert_rules.go |

---

## Seuils du calculateur de dimming

| Condition | Seuil | Résultat |
|---|---|---|
| Protection thermique | Température > 75 °C | Intensité ≤ 50 % |
| Présence + obscurité | Luminosité < 30 lux | Intensité 90 % |
| Nuit creuse | Heure ∈ [0h, 5h[ | Intensité 30 % |
| Obscurité sans présence | Luminosité < 30 lux | Intensité 50 % |
| Lumière naturelle | Luminosité > 70 lux | Intensité 20 % |
| Défaut | — | Intensité 60 % |

---

## Seuils de signal radio

| Niveau | Valeur | Qualité | Impact |
|---|---|---|---|
| Excellent | > 60 dBm | Très bonne | Pas de pénalité |
| Acceptable | 30–60 dBm | Modérée | −10 pts communication |
| Faible | < 30 dBm | Mauvaise | −25 pts communication |

---

## Seuils de taux de panne par zone

| Taux de panne | Points risque zone | Signification |
|---|---|---|
| > 0 % | +20 | Pannes ponctuelles |
| ≥ 40 % | +40 | Défaillance majeure |
| ≥ 80 % | +60 | Défaillance quasi-totale |

---

## Seuils de taux de panne LCU

| Taux de lampadaires hors ligne (LCU) | Points risque | Signification |
|---|---|---|
| > 30 % | +15 | Zone de panne radio probable |
| LCU hors ligne | +40 | Perte totale supervision |

---

## Seuils d'efficacité énergétique

| Condition | Points | Signification |
|---|---|---|
| Intensité moyenne ≥ 90 % | −25 sur score efficacité | Dimming non utilisé |
| Puissance mesurée > nominal × 0.90 | −20 sur score efficacité | Légère surconsommation |

---

## Seuils économiques (tarifs de référence)

| Paramètre | Valeur actuelle | Configurable ? | Note |
|---|---|---|---|
| Tarif kWh | **1.20 DH/kWh** | Oui (future version) | Tarif de référence Maroc |
| Facteur CO₂ | **0.638 kg CO₂/kWh** | Oui (future version) | ONEE Maroc indicatif |
| Réduction estimée dimming nuit | **45 %** | Non (hardcodé) | Hypothèse de calcul |
| Durée nuit estimée | **5 h** | Non (hardcodé) | Hypothèse de calcul |

---

## Plan de configuration des seuils (version entreprise)

Dans une version production, les seuils doivent être :

1. **Configurables par type de luminaire** : un LED 250 W a un profil thermique différent d'un 50 W.
2. **Configurables par zone** : une zone industrielle peut tolérer des températures driver plus élevées qu'une zone résidentielle.
3. **Configurables par client** : chaque municipalité a son propre contrat électrique (tarif DH/kWh différent).
4. **Stockés en base de données** : dans la table `system_settings` déjà présente dans la plateforme.
5. **Modifiables via l'interface admin** : sans recompilation du code.

---

## Limites et hypothèses

- Les seuils actuels sont des valeurs de référence industrielles génériques. Ils n'ont pas été validés sur des données terrain de la plateforme Lamalif.
- Le tarif kWh de 1.20 DH doit être mis à jour selon le contrat réel avec l'opérateur électrique.
- Le facteur CO₂ de 0.638 kg/kWh est indicatif et doit être mis à jour annuellement depuis les publications de l'ONEE.
- Les seuils de signal dBm peuvent varier selon la technologie radio utilisée (LoRa, Zigbee, NB-IoT).

## Source technique

`smart-lighting-ai/app/recommendations/utils.py` : TELEMETRY_STALE_HOURS, WO_CRITICAL_HOURS, WO_OLD_HOURS, DRIVER_TEMP_CRITICAL, DRIVER_TEMP_HIGH
`smart-lighting-web/backend/internal/services/alert_rules.go` : seuils alertes
`smart-lighting-web/backend/internal/services/calculator.go` : seuils dimming
