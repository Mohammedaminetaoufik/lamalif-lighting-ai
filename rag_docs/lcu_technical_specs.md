# Spécifications Techniques LCU (Luminaire Control Unit)

## Définition et rôle du LCU

Un LCU (Luminaire Control Unit) est un contrôleur de point lumineux installé dans ou sur un luminaire d'éclairage public. Il pilote le driver LED (dimming), remonte les mesures de consommation, de température et d'état, et communique avec le CMS (Central Management System) via un protocole radio ou filaire.

Le LCU est l'unité de terrain. Il ne prend aucune décision autonome sur les interventions physiques — toute action de dimming ou d'extinction est validée par un opérateur humain via le CMS.

## Fonctions principales d'un LCU

- Contrôle du niveau d'éclairage (dimming) : 0–100 % via DALI, DALI-2, D4i, 0-10V, SR, Dexal
- Mesure de consommation active (W) et réactive (VAR)
- Relevé de tension (V), courant (mA), facteur de puissance (cos φ)
- Mesure de température interne du driver
- Compteur d'heures de fonctionnement (working time)
- Compteur de démarrages (start counter)
- Détection de pannes : lampe absente, défaut driver, court-circuit DALI
- Horodatage GPS ou NTP pour les programmes horaires
- Stockage local des mesures en cas de perte de communication
- Remontée d'alarmes vers le CMS

## Interfaces de montage

### NEMA (ANSI C136.10)
- Standard nord-américain
- Prise 5 ou 7 broches sur la tête de luminaire
- Connecteur rond, twist-lock
- Commun sur les candélabres de voirie

### Zhaga Book 18
- Standard européen IEC 62717 / IEC 62722
- Interface D4i-compatible : données DALI + alimentation 24V sur le même connecteur
- Connecteur 4 broches (2 puissance + 2 signal)
- Permet le plug-and-play : remplacement sans outil
- Compatible avec les sockets Zhaga Book 18 intégrés dans le luminaire

### Intégration externe (pole-mount / internal)
- Montage sur mât ou en interne dans le boîtier luminaire
- Utilisé quand ni NEMA ni Zhaga n'est disponible

## Protocoles de communication supportés

### RF Mesh 2,4 GHz (Zigbee / propriétaire)
- Réseau maillé auto-cicatrisant
- Portée nœud-à-nœud : 100–300 m
- Fréquence : 2,4 GHz (ISM)
- Latence : < 1 s
- Débit : 250 kbps

### LPWAN — LoRaWAN
- Portée : 1–5 km urbain, jusqu'à 15 km rural
- Fréquence : 868 MHz (Europe), 915 MHz (Amérique)
- Débit : 0,3–50 kbps (SF7–SF12)
- Latence : 2–5 s
- Topologie : étoile (LCU → passerelle → réseau cloud)
- 100–200 nœuds par passerelle

### NB-IoT (Narrowband IoT)
- Portée : couverte par cellule 4G/LTE (10–15 km)
- Fréquence : bandes LTE sous-GHz
- Débit : < 100 kbps
- Latence : 1–10 s
- Topologie : cellulaire direct, pas de passerelle locale
- Coût : abonnement SIM par LCU (plus élevé)

### PLC (Power Line Communication)
- Communication via le câble d'alimentation existant (230V)
- Pas de radio, pas de câblage supplémentaire
- Fréquence : 9–148,5 kHz (CENELEC A) ou bandes PRIME/G3-PLC
- Débit : 1–10 kbps (PRIME) ou jusqu'à 300 kbps (G3-PLC)
- Fiable dans les tunnels et zones souterraines
- Sensible aux perturbations harmoniques du réseau électrique

## Protocole TALQ

TALQ (Technically Aligned for Luminaire Quality) est un protocole standard de communication entre les LCU de terrain (appelés "gateway devices" ou "outdoor device gateways") et le CMS.

### Caractéristiques TALQ
- Architecture : RESTful HTTP/HTTPS, JSON, TCP/IP
- Encapsulation : objets JSON standardisés (DataModel)
- Certifié par le TALQ Consortium (www.talq-consortium.org)
- Interopérabilité multi-fournisseurs : CMS ↔ LCU de marques différentes
- Version actuelle : TALQ 2.x

### Objets TALQ principaux
- `Programme horaire` (calendar program) : définition des profils de dimming
- `Mesures` (measurement values) : puissance, énergie, état
- `Alarmes` (alarms) : pannes, seuils dépassés
- `Commandes` (commands) : dimming, extinction, redémarrage

### Flux TALQ
1. CMS envoie un programme horaire au LCU (push)
2. LCU applique le programme localement
3. LCU remonte les mesures au CMS selon la période de polling
4. CMS détecte les anomalies et crée des alertes

## Fabricants LCU courants

### Tvilight (Pays-Bas)
- Gamme CitySense (avec capteur de mouvement intégré)
- Protocoles : RF Mesh 2,4 GHz, NB-IoT, LTE Cat M1, 2G
- Interfaces dimming : DALI, DALI-2, D4i, 0-10V, SR, Dexal
- Montage : NEMA, Zhaga Book 18, externe, interne
- TALQ-certifié
- CMS : CityManager (cloud ou on-premise)
- API ouverte pour intégration tiers

### Schreder Owlet
- Intégré dans les luminaires Schreder
- Communication : LoRaWAN, NB-IoT, RF Mesh
- Interface D4i native
- Montage Zhaga Book 18 standard

### Telensa (UK)
- Gamme PLANet
- Communication : Telensa Ultra Narrowband (UNB) propriétaire
- Portée : > 5 km en zone urbaine
- Faible consommation radio (µW)

### Schréder, Philips / Signify, Siteco, Osram
- Proposent des solutions LCU intégrées ou compatibles TALQ

## Paramètres surveillés par le LCU (données remontées au CMS)

| Paramètre | Unité | Utilité |
|-----------|-------|---------|
| Puissance active | W | Détection anomalie consommation |
| Puissance apparente | VA | Calcul facteur de puissance |
| Énergie cumulée | kWh | Facturation, reporting |
| Tension réseau | V | Détection surtension / sous-tension |
| Courant lampe | mA | Détection lampe absente (0 mA) |
| Facteur de puissance | - | Qualité réseau |
| Température driver | °C | Détection surchauffe |
| Niveau de dimming actuel | % | Vérification exécution programme |
| Heures de fonctionnement | h | Planification maintenance |
| Compteur de démarrages | count | Surveillance allumages anormaux |
| État DALI | code | Diagnostic bus DALI |
| Signal radio (RSSI) | dBm | Qualité liaison communication |
| Timestamp dernière communication | datetime | Détection LCU hors ligne |

## Diagnostics LCU courants

### LCU hors ligne
- Causes : panne alimentation, défaut radio, antenne endommagée, gel du firmware
- Impact : perte de contrôle de tous les lampadaires du groupe
- Priorité : CRITIQUE si > 1 LCU hors ligne dans une zone active

### LCU partiellement fonctionnel
- Communication active mais bus DALI en erreur
- Driver DALI ne répond pas aux commandes de dimming
- Mesures reçues mais commandes non exécutées

### LCU en alarme de température
- Température interne driver > 70°C : avertissement
- Température interne driver > 85°C : alarme critique, risque de dommage permanent
- Cause possible : dissipation thermique insuffisante, chaleur ambiante estivale

## Calcul du health_score LCU

Le health_score est calculé sur la base de :
- 0 = LCU complètement hors ligne (non joignable depuis > 24h)
- 1–40 = pannes graves (DALI KO, 50% lampadaires hors ligne)
- 41–70 = dégradé (communication instable, température élevée)
- 71–90 = bon avec avertissements mineurs
- 91–100 = nominal

Un health_score < 50 sur plusieurs LCUs dans la même zone indique un problème de réseau ou d'infrastructure commune (alimentation secteur, armoire électrique).
