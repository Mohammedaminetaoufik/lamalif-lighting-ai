# Règles de Diagnostic par Équipement — Smart Lighting

Ce fichier définit les règles et méthodologies pour analyser individuellement un lampadaire ou une LCU.

---

## Diagnostic d'un Lampadaire

### Vues à utiliser (dans cet ordre)

1. `ai_lampadaire_status` — État général, LCU associée, intensité, localisation
2. `ai_lampadaire_diagnostics` — Diagnostic technique, températures, compteurs d'alertes
3. `ai_telemetry_latest` — Dernières mesures physiques
4. `ai_open_alerts` — Alertes ouvertes liées à ce lampadaire
5. `ai_workorders` — Bons de travail en cours liés

### Analyse attendue

**État actuel :**
- Quel est l'état (online/offline/maintenance) ?
- Depuis quand est-il dans cet état (last_seen_at) ?
- Est-il en panne ou en maintenance volontaire ?

**LCU associée :**
- Quelle LCU contrôle ce lampadaire ?
- La LCU est-elle en ligne ?
- D'autres lampadaires de la même LCU sont-ils offline ?

**Télémétrie récente :**
- Quelle est la température du driver (driver_temperature) ?
- Quelle est la puissance consommée (last_power) ?
- Y a-t-il eu une mesure récente (last_measure_at) ?
- Les valeurs sont-elles dans les plages normales ?

**Alertes ouvertes :**
- Combien d'alertes sont ouvertes (open_alerts_count) ?
- Y a-t-il des alertes critiques (critical_alerts_count) ?
- Quelle est la cause probable indiquée par les alertes ?

**Interventions liées :**
- Un bon de travail est-il déjà ouvert pour ce lampadaire ?
- Quel est son statut et son ancienneté ?

**Priorité calculée :**
- critical : offline + alertes critiques + température élevée
- high : offline OU alertes critiques
- medium : en maintenance OU alertes warning
- low : en ligne, fonctionnel

### Exemple de questions RAG pour un lampadaire

- "Règles de diagnostic pour un lampadaire offline"
- "Comment analyser un lampadaire avec température driver élevée"
- "Recommandations pour lampadaire sans télémétrie récente"
- "Que faire si un lampadaire a des alertes critiques"

---

## Diagnostic d'une LCU

### Vues à utiliser (dans cet ordre)

1. `ai_lcu_status` — Statut réseau, compteurs lampadaires, dernière sync
2. `ai_lcu_health` — Health score, alertes liées
3. `ai_lampadaire_status` — Lampadaires rattachés à cette LCU
4. `ai_open_alerts` — Alertes liées à cette LCU
5. `ai_workorders` — Bons de travail liés à cette LCU

### Analyse attendue

**Statut réseau :**
- La LCU est-elle en ligne (status = 'online') ?
- Depuis quand a-t-elle communiqué (last_seen_at) ?
- Sa dernière synchronisation est-elle récente (last_sync_at) ?

**Santé globale :**
- Quel est son health_score (0-100) ?
- Un score < 50 indique une LCU critique nécessitant une intervention
- Un score 50-80 indique une LCU dégradée à surveiller

**Lampadaires rattachés :**
- Combien de lampadaires sont online (online_count) ?
- Combien sont offline (offline_count) ?
- Combien sont en maintenance (maintenance_count) ?
- Le taux d'offline (offline_count / lampadaires_count) est-il élevé ?

**Impact global :**
- Combien de points d'éclairage sont impactés ?
- La panne de cette LCU affecte-t-elle une zone entière ?
- Quelle est l'urgence de l'intervention ?

**Alertes et interventions :**
- Des alertes critiques sont-elles liées à cette LCU ?
- Un bon de travail est-il déjà ouvert pour cette LCU ?

**Priorité calculée :**
- critical : LCU offline + lampadaires_offline élevé + alertes critiques
- high : LCU offline OU health_score < 30 OU offline_count > 5
- medium : health_score 30-60 OU offline_count 1-5
- low : LCU en ligne, health_score > 80

### Recommandations LCU

Si la LCU est offline :
1. Vérifier l'alimentation électrique de la LCU
2. Vérifier la connectivité réseau IP/LoRaWAN
3. Tenter une reconnexion depuis l'interface
4. Si échec : planifier une intervention terrain

Si health_score < 50 :
1. Analyser les lampadaires offline liés
2. Vérifier la dernière synchronisation
3. Contrôler les alertes actives
4. Planifier une maintenance préventive

### Exemple de questions RAG pour une LCU

- "Règles de diagnostic pour une LCU critique avec health_score faible"
- "Comment analyser une LCU avec de nombreux lampadaires offline"
- "Recommandations pour une LCU sans synchronisation récente"

---

## Schéma de corrélation équipements

Un lampadaire offline peut être causé par :
- Panne LCU (impact collectif — vérifier LCU en premier)
- Panne d'alimentation locale (impact individuel)
- Panne driver LED (impact individuel, fault_status non nul)
- Perte de communication contrôleur (signal faible)
- Maintenance volontaire (etat = 'maintenance')

Ordre de diagnostic recommandé :
1. Vérifier si la LCU associée est online
2. Vérifier si d'autres lampadaires de la même LCU sont offline
3. Si oui → problème LCU centralisé
4. Si non → problème individuel → inspecter le lampadaire
