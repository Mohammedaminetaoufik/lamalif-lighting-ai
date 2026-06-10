# Spécifications Drivers LED et Protocoles DALI / D4i

## Qu'est-ce qu'un driver LED

Un driver LED est l'alimentation électronique qui convertit le courant secteur (230V AC) en courant continu régulé pour alimenter les LEDs. Il assure :
- La stabilité du courant de sortie (mA constant)
- Le dimming (variation de l'intensité lumineuse)
- La protection thermique et contre les surcharges
- La remontée des données de diagnostic (avec D4i)

Les drivers LED sont le composant le plus souvent responsable des défaillances dans un luminaire (pas les LEDs elles-mêmes).

## DALI (Digital Addressable Lighting Interface) — IEC 62386

### DALI original (version 1)
- Bus numérique 2 fils (non polarisé)
- 64 adresses individuelles par bus (0–63)
- 16 groupes d'adressage
- Portée max bus : 300 m (résistance < 8 Ω)
- Alimentation bus : 9,5–22,5 V DC (fournie par le contrôleur DALI)
- Courant bus max : 250 mA
- Vitesse : 1200 bauds (asynchrone)
- Résolution dimming : 256 niveaux (0–254, 255 = MASK)
- Certification : auto-déclarée par le fabricant

### DALI-2 — IEC 62386 Part 103
- Compatibilité ascendante avec DALI original
- 128 adresses individuelles par bus
- Certification obligatoire par organisme tiers (DALI Alliance)
- Meilleure interopérabilité multi-fabricants
- Support bidirectionnel renforcé (requête d'état)
- Types d'équipements standardisés (DT0–DT8) :
  - DT6 : LED driver
  - DT7 : variateur pour lampes à filament
  - DT8 : couleur et température de couleur (CCT)

## D4i — DALI for IoT (IEC 62386 Part 25X)

D4i est une extension de DALI-2 spécifiquement conçue pour l'éclairage public connecté. Il ajoute des parties de données (data parts) standardisées pour la remontée d'informations depuis le driver.

### Part 250 — Alimentation auxiliaire (Power Interface)
- Fourniture d'une tension auxiliaire 24V DC sur le bus D4i
- Puissance : 3W en moyenne, 6W en pointe
- Permet d'alimenter le LCU directement depuis le driver
- Élimine le besoin d'une alimentation séparée pour le module de contrôle

### Part 251 — Données luminaire (Luminaire Data)
Données identitaires du driver et du luminaire :
- Puissance nominale (W)
- Tension de sortie nominale (V)
- Courant de sortie nominal (mA)
- Température de couleur (CCT) en Kelvin
- Indice de rendu des couleurs (CRI / Ra)
- Coordonnées chromatiques (x, y)
- Données fabricant (manufacturer code, product ID)
- Données de configuration initiale

### Part 252 — Données énergie (Energy Data)
Mesures énergétiques en temps réel :
- Puissance active consommée (W) — résolution 0,1 W
- Puissance apparente (VA)
- Énergie active cumulée (kWh) — compteur non réinitialisable
- Énergie réactive cumulée (kVArh)
- Facteur de puissance (cos φ)
- Tension réseau mesurée (V)
- Fréquence réseau (Hz)

Ces données permettent la facturation d'énergie par point lumineux et la détection d'anomalies de consommation.

### Part 253 — Données diagnostics (Diagnostic and Maintenance)
Paramètres de diagnostic pour la maintenance prédictive :
- **Conditions de panne** :
  - LED failure (court-circuit ou circuit ouvert détecté)
  - Driver failure (panne interne driver)
  - Overtemperature (dépassement température critique)
  - Undervoltage / Overvoltage
  - Overcurrent
  - Calibration failure
- **Compteurs opérationnels** :
  - Heures de fonctionnement totales (working time en heures)
  - Compteur de démarrages / allumages (start counter)
- **Mesures thermiques** :
  - Température interne du driver (°C) — point de mesure : condensateur ou driver IC
  - Température de jonction LED estimée (°C) si disponible
- **Courant de sortie LED actuel** (mA) — valeur réelle vs nominale
- **Facteur de puissance actuel** — dégradation indique vieillissement condensateur
- **Niveau de flux lumineux** (%) — dépréciement mesuré si luxmètre intégré

## Comparatif DALI vs DALI-2 vs D4i

| Critère | DALI | DALI-2 | D4i |
|---------|------|--------|-----|
| Norme | IEC 62386 | IEC 62386 Part 103 | IEC 62386 Part 25X |
| Adresses | 64 | 128 | 128 |
| Certification | Auto-déclarée | Tiers obligatoire | Tiers obligatoire |
| Interopérabilité | Bonne | Excellente | Excellente |
| Alimentation auxiliaire | Non | Non | Oui (24V, 3W) |
| Données énergie | Non | Non | Oui (Part 252) |
| Données diagnostics | Non | Non | Oui (Part 253) |
| Données luminaire | Non | Non | Oui (Part 251) |
| Maintenance prédictive | Impossible | Impossible | Native |

## Zhaga Book 18 + D4i

L'association du socket Zhaga Book 18 avec D4i crée le standard "Zhaga-D4i" :
- Connecteur 4 broches normalisé (plug-and-play)
- Broche 1-2 : alimentation 24V DC (D4i Part 250)
- Broche 3-4 : bus DALI bidirectionnel
- Le LCU se connecte directement sur le socket sans câblage supplémentaire
- Remplacement du LCU en < 2 minutes sans outil
- Interchangeable entre fabricants certifiés Zhaga-D4i

## Interface 0-10V (analogique)

- Plus ancienne, plus simple
- Tension de contrôle : 0V = éteint, 10V = 100% flux
- Unidirectionnelle : pas de remontée d'état
- Pas de diagnostic possible
- Utilisée sur les drivers et ballasts anciens
- Progressivement remplacée par DALI/D4i dans les nouvelles installations

## Paramètres driver surveillés dans le système

Dans la base de données télégestion, les données driver remontées via D4i Part 252/253 sont accessibles dans les vues :
- `ai_lampadaires_details` : puissance, courant, température
- `ai_energy_overview` : consommation cumulée par lampadaire
- `ai_lampadaires_health` : health_score intégrant les alarmes driver

### Seuils d'alerte driver
| Paramètre | Avertissement | Critique |
|-----------|---------------|---------|
| Température driver | > 70°C | > 85°C |
| Courant sortie vs nominal | ± 15% | ± 30% |
| Facteur de puissance | < 0,85 | < 0,70 |
| Heures fonctionnement | > 40 000 h | > 50 000 h |
| Compteur démarrages | > 5 000 | > 10 000 |

## Causes courantes de défaillance driver

### 1. Condensateurs électrolytiques (cause n°1)
- Composant à durée de vie limitée dans le driver
- Mécanisme : évaporation de l'électrolyte sous chaleur
- Durée de vie nominale : 20 000–50 000 h à 25°C
- Loi d'Arrhenius : chaque +10°C réduit la durée de vie de 50%
- À 70°C ambiant → durée de vie réduite à 1/8 de la valeur nominale
- Symptôme : facteur de puissance dégradé, ondulation courant, chauffage anormal

### 2. Transistors MOSFET de commutation
- Dégradation par cyclage thermique
- Symptôme : courant instable, bruit électromagnétique

### 3. Circuit de contrôle PWM
- Dérive des références de tension avec le vieillissement
- Symptôme : dimming imprécis, sauts de niveau

### 4. Défaut d'isolation
- Infiltration d'humidité dans le boîtier
- Corrosion des soudures (problème spécifique zones côtières)

### 5. Surtension réseau
- Pics de tension lors de commutation de charges inductives
- Protection par MOV (varistance) ou TVS diode

## Cycle de vie typique driver LED éclairage public

- Durée garantie fabricant : 50 000 h (L'70, Ta=25°C)
- Durée de vie réelle en conditions terrain (Ta=40°C) : 25 000–35 000 h
- Durée de vie en zone à fortes variations thermiques : 20 000–30 000 h
- Intervalle de remplacement préventif recommandé : 40 000 h ou 12 ans

Un lampadaire fonctionnant 4 000 h/an atteint 40 000 h en 10 ans.
