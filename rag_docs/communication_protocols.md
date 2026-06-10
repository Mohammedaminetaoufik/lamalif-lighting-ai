# Protocoles de Communication Éclairage Public Connecté

## Vue d'ensemble

Les LCUs (Luminaire Control Units) utilisent différents protocoles de communication radio ou filaires pour transmettre leurs données vers le CMS (Central Management System). Le choix du protocole impacte directement la portée, le coût d'infrastructure, la scalabilité et la fiabilité du système.

## Tableau comparatif complet

| Critère | LoRaWAN | Zigbee | NB-IoT | PLC |
|---------|---------|--------|--------|-----|
| **Support physique** | Radio RF | Radio RF | Cellulaire LTE | Câble 230V |
| **Fréquence** | 868 MHz (EU) / 915 MHz (US) | 2,4 GHz | Bandes LTE sub-GHz | 9–148,5 kHz |
| **Portée nœud** | 1–5 km urbain, 15 km rural | 100–300 m | Couverture cellulaire | Réseau électrique local |
| **Débit max** | 0,3–50 kbps (SF7–SF12) | 250 kbps | < 100 kbps | 1–300 kbps (selon norme) |
| **Latence typique** | 2–5 s | < 1 s | 1–10 s | 0,5–2 s |
| **Topologie** | Étoile (LCU → gateway → cloud) | Mesh auto-cicatrisant | Direct cellulaire | Bus sur ligne électrique |
| **Nœuds/gateway** | 100–1 000 | 200–500 | ~200 000/cellule | Illimité (même réseau) |
| **Coût infrastructure** | Moyen (passerelles) | Moyen | Élevé (SIM + data) | Bas (câble existant) |
| **Coût par nœud** | Bas | Bas-Moyen | Élevé (abonnement SIM) | Bas |
| **Résistance interférences** | Excellente | Faible (2,4 GHz saturé) | Bonne | Variable (harmoniques) |
| **Pénétration bâtiment** | Bonne | Faible | Excellente | N/A |
| **Tunnels/souterrain** | Mauvaise | Mauvaise | Variable | Excellente |
| **Consommation radio LCU** | Très faible (µA en veille) | Faible (mA) | Faible (eDRX) | Nulle |
| **Fiabilité** | ★★★★ | ★★★ | ★★★★ | ★★★★★ |
| **Scalabilité** | ★★★★★ | ★★★ | ★★★★★ | ★★★★ |

## LoRaWAN — Long Range Wide Area Network

### Principes techniques
- Modulation : LoRa (Chirp Spread Spectrum) développée par Semtech
- Facteurs d'étalement (Spreading Factor) : SF7 à SF12
  - SF7 : débit max (50 kbps), portée min, batterie longue durée
  - SF12 : débit min (0,3 kbps), portée max, batterie plus courte
- Largeur de bande : 125 kHz ou 250 kHz
- EIRP max Europe : 14 dBm (25 mW) en bande 868 MHz
- Canal obligatoire EU868 : 868,1 / 868,3 / 868,5 MHz

### Architecture LoRaWAN
```
LCU (end device) → Passerelle LoRa (gateway) → Network Server → Application Server → CMS
```
- Une passerelle couvre 1–5 km² en milieu urbain
- Les passerelles sont passives (transmet tout, filtre en réseau serveur)
- Possibilité de réseau privé (The Things Network, ChirpStack) ou opérateur (Orange, Bouygues)

### Avantages LoRaWAN pour éclairage public
- Pas de SIM, pas d'abonnement opérateur si réseau privé
- Infrastructure passerelle mutualisable avec d'autres IoT (eau, déchets)
- Très faible coût par nœud (< 5€/an si réseau propre)
- Adapté aux zones peu denses (rural, périurbain)

### Limites LoRaWAN
- Duty cycle limité : 1% en Europe (régulation ETSI)
  → Maximum ~36 secondes de transmission par heure par LCU
  → Limites la fréquence de remontée de mesures
- Latence élevée : commandes de dimming non temps-réel
- Pas adapté aux flux continus de données (streaming énergétique)

## Zigbee — Mesh Radio 2,4 GHz

### Principes techniques
- Standard : IEEE 802.15.4 + couche réseau Zigbee Alliance (CSA)
- Fréquence : 2,4 GHz (16 canaux, 5 MHz espacement)
- Débit PHY : 250 kbps
- Portée nœud-à-nœud : 100–300 m en extérieur (selon obstacles)
- Puissance TX : 0–20 dBm selon profil

### Architecture Zigbee
```
Lampadaire A (router) ←→ Lampadaire B (router) ←→ ... ←→ Gateway (coordinator) → CMS
```
- Topologie mesh : chaque LCU est un routeur pour ses voisins
- Auto-réparation : si un nœud tombe, le trafic contourne automatiquement
- Coordinator (gateway) : 1 seul par réseau, point central de contrôle
- Profil ZigBee 3.0 : standardisé, interopérable

### Avantages Zigbee
- Faible latence (< 1 s) : adapté aux commandes de dimming quasi-temps-réel
- Débit suffisant pour les mesures énergétiques détaillées
- Maillage robuste dans les zones denses (villes avec lampadaires tous les 30 m)
- Coût d'infrastructure faible si les LCUs servent de routeurs

### Limites Zigbee
- Interférences sévères en 2,4 GHz (Wi-Fi, Bluetooth, micro-ondes)
- Portée limitée : nécessite densité élevée de lampadaires
- Point de défaillance unique (coordinator) si non redondé
- Profondeur de mesh max : 10–15 sauts (latence augmente avec la distance)
- Consommation plus élevée que LoRaWAN

### Cas d'usage Zigbee
- Centres-villes à forte densité de lampadaires (espacement < 30 m)
- Zones avec infrastructure Wi-Fi déjà gérée (risque interférences connu)
- Projets nécessitant un temps de réponse rapide aux commandes

## NB-IoT — Narrowband IoT (3GPP Release 13)

### Principes techniques
- Technologie cellulaire (opérateur télécom)
- Bandes : LTE Band 8 (900 MHz), Band 20 (800 MHz), Band 28 (700 MHz)
- Débit downlink : 26 kbps, uplink : 62 kbps (half-duplex)
- Couverture : identique au réseau LTE de l'opérateur
- MCL (Maximum Coupling Loss) : 164 dB (+20 dB vs LTE standard)
- eDRX (Extended Discontinuous Reception) : économie batterie

### Architecture NB-IoT
```
LCU → Antenne BTS opérateur (LTE) → Core network opérateur → IoT Platform → CMS
```
- Pas de passerelle locale à déployer
- Itinérance possible (roaming 4G)
- SLA opérateur (99,9% uptime garanti)

### Avantages NB-IoT
- Couverture nationale immédiate si opérateur partenaire
- Idéal pour déploiements dispersés sur grands territoires
- Pas d'infrastructure réseau à gérer
- Pénétration intérieure excellente (sous-sols, garages)
- Scalabilité illimitée (facturation par SIM)

### Limites NB-IoT
- Coût récurrent : abonnement SIM + data par lampadaire (5–15 €/an/LCU)
- Dépendance opérateur télécom (couverture, tarifs, continuité service)
- Latence variable (1–10 s)
- Débit insuffisant pour firmware updates (OTA) volumineux
- Cas d'usage critique : si l'opérateur coupe le service, le système perd tous les LCUs

## PLC — Power Line Communication

### Principes techniques
- Communication sur le câble d'alimentation 230V existant
- Aucun câble radio ni déploiement de passerelles
- Standards principaux :
  - CENELEC EN 50065 : bandes A (9–95 kHz), B/C/D (95–148,5 kHz)
  - PRIME (ITU-T G.9904) : OFDM, 42,24 kbps, bande CENELEC A
  - G3-PLC (ITU-T G.9903) : jusqu'à 300 kbps, IPv6 natif, robust pour bruit
  - IEEE 1901.2 : standard américain compatible G3-PLC

### Architecture PLC
```
LCU → Câble 230V → Concentrateur PLC (dans armoire) → CMS
```
- Le concentrateur est installé dans l'armoire électrique de rue
- 1 concentrateur par réseau de distribution (armoire)
- Pas de passerelle radio, pas de SIM

### Avantages PLC
- Infrastructure existante (câble 230V) : coût de déploiement minimal
- Fiabilité maximale dans les tunnels, sous-sols, zones RF dégradées
- Latence faible (< 2 s)
- Pas de perturbation radio (aucune émission RF)
- Idéal pour les routes nationales, autoroutes, tunnels

### Limites PLC
- Sensible aux harmoniques et bruit du réseau électrique
- Atténuation forte sur les câbles vieux ou de mauvaise qualité
- Distance max efficace : 300–500 m par segment (concentrateur)
- Nécessite des coupleurs PLC sur chaque armoire
- Débit limité comparé aux technologies radio

## Recommandations de choix de protocole

| Contexte | Protocole recommandé |
|----------|----------------------|
| Ville dense, lampadaires < 30m | Zigbee ou RF Mesh 2,4 GHz |
| Zone périurbaine / rural étendu | LoRaWAN |
| Territoire national dispersé | NB-IoT |
| Tunnel, autoroute, sous-sol | PLC |
| Interopérabilité multi-fournisseurs | LoRaWAN ou NB-IoT + TALQ |
| Budget infrastructure limité | PLC (câble existant) ou LoRaWAN |
| Temps de réponse critique (< 1s) | Zigbee ou PLC |

## RSSI et qualité signal

Le RSSI (Received Signal Strength Indicator) est remonté par les LCUs radio :
- RSSI > -80 dBm : excellente qualité signal
- RSSI -80 à -100 dBm : qualité acceptable
- RSSI -100 à -110 dBm : signal faible, risque de pertes
- RSSI < -110 dBm : signal critique, risque de déconnexion

Un RSSI < -105 dBm sur plusieurs LCUs dans la même zone indique un problème d'infrastructure radio (passerelle défaillante ou obstruée).

## Diagnostic communication dans le système télégestion

Les données de communication disponibles dans les vues `ai_*` :
- `ai_lcus_status` : signal_qualite (RSSI ou équivalent), last_seen_at
- `ai_alertes_actives` : alertes de type "communication_lost"
- `ai_zone_overview` : pourcentage LCUs hors ligne par zone

### Règles de diagnostic communication
- 1 LCU hors ligne → problème local (alimentation ou LCU défaillant)
- Plusieurs LCUs hors ligne dans même zone → problème passerelle ou réseau commun
- RSSI dégradé sans perte totale → obstruction nouvelle (construction, végétation)
- Perte totale après mise à jour firmware → rollback nécessaire
