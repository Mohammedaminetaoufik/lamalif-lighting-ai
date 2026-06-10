# Règles de Recommandation — Smart Lighting Télégestion

Ce fichier définit les recommandations opérationnelles à donner selon les situations détectées.

---

## Situation : LCU critique ou offline

**Symptômes :** LCU offline, health_score < 50, offline_count élevé, alertes critiques liées.

**Recommandations :**
1. Vérifier l'alimentation électrique de la LCU (coupure, disjoncteur)
2. Vérifier la connectivité réseau IP : ping, route réseau, VLAN
3. Contrôler la dernière synchronisation (last_sync_at) — si > 30 min, intervention requise
4. Vérifier le concentrateur ou la passerelle réseau associée
5. Ne pas créer d'intervention individuelle pour chaque lampadaire lié avant analyse LCU
6. Si la LCU est accessible, relancer la synchronisation depuis l'interface
7. En cas d'échec : intervention terrain sur la LCU en priorité

---

## Situation : Lampadaires hors ligne

**Symptômes :** etat = 'offline', last_seen_at ancien.

**Recommandations :**
1. Vérifier d'abord la LCU associée (lcu_reference) — si elle est offline, c'est la cause probable
2. Si la LCU est en ligne, analyser le lampadaire individuellement
3. Vérifier la dernière communication (last_seen_at)
4. Contrôler l'alimentation locale (coffret, disjoncteur, fusible)
5. Vérifier le driver LED (fault_status)
6. Contrôler si une alerte ou un bon de travail existe déjà avant d'en créer un nouveau
7. Vérifier si d'autres lampadaires voisins sont également offline (problème collectif)

---

## Situation : Température driver élevée (> 70°C)

**Symptômes :** driver_temperature > 70 dans ai_driver_health.

**Recommandations :**
1. Vérifier la ventilation du luminaire et la dissipation thermique
2. Contrôler le courant de sortie du driver (output_current_ma) — surcharge possible
3. Vérifier si la protection surtension (surge_protection) est active
4. Inspecter l'environnement thermique du lampadaire (exposition solaire directe, compartiment fermé)
5. Planifier une inspection terrain dans les 24-48h
6. Si température > 85°C, intervention urgente pour éviter la défaillance du driver
7. Réduire l'intensité temporairement sous validation humaine si possible

---

## Situation : Consommation énergétique anormalement élevée

**Symptômes :** total_energy_kwh ou avg_measured_power_w très au-dessus de la moyenne dans ai_energy_summary.

**Recommandations :**
1. Vérifier les profils de dimming actifs dans la zone concernée
2. Analyser si des lampadaires sont bloqués à 100% d'intensité
3. Comparer avec les autres zones pour identifier les anomalies
4. Proposer une optimisation progressive du dimming — sous validation humaine obligatoire
5. Vérifier si des drivers consomment plus que leur puissance nominale
6. Si l'écart est > 20% par rapport à la moyenne, créer un bon de travail d'analyse

---

## Situation : Commissioning bloqué

**Symptômes :** test_comm_status ou test_dimming_status = 'failed', commissioning_status non 'commissioned'.

**Recommandations :**
1. Vérifier la liaison physique entre le lampadaire et la LCU
2. Tester la communication (test_comm_status) : si 'failed', problème de connectivité
3. Relancer le test de dimming (test_dimming_status) : si 'failed', problème driver ou câblage
4. Vérifier les coordonnées GPS : commissioning impossible sans localisation
5. Valider uniquement si TOUS les tests sont en 'success'
6. Ne pas forcer la validation sans tests complets
7. Documenter la cause du blocage dans commissioning_notes

---

## Situation : Bon de travail ancien (age_hours élevé)

**Symptômes :** age_hours > 72 heures, statut toujours ouvert.

**Recommandations :**
1. Remonter la priorité du bon de travail si l'équipement est critique
2. Vérifier si le technicien assigné est disponible (ai_technician_workload)
3. Si bloqué depuis > 7 jours, escalader vers un responsable
4. Traiter les interventions critiques (priority = 'critical') avant les interventions normales
5. Si le lampadaire est toujours offline après 48h, créer un nouveau bon de travail urgent

---

## Situation : Signal contrôleur faible (< 40)

**Symptômes :** controller_signal_quality < 40 dans ai_controller_network_status.

**Recommandations :**
1. Vérifier l'orientation et la position de l'antenne du contrôleur
2. Vérifier l'absence d'obstacles ou interférences électromagnétiques
3. Contrôler le firmware du contrôleur (controller_firmware) — mise à jour possible
4. Si signal < 20, intervention terrain pour vérifier le matériel
5. Comparer avec les contrôleurs voisins pour identifier un problème localisé

---

## Situation : Alertes critiques multiples sur une zone

**Symptômes :** critical_alerts_count > 3 dans ai_zone_health ou ai_alert_summary.

**Recommandations :**
1. Analyser la LCU de la zone pour identifier un problème centralisé
2. Vérifier si les alertes partagent le même type (lampadaire_offline, communication, etc.)
3. Prioriser les interventions selon la densité et l'importance de la zone
4. Créer un bon de travail de zone si plus de 5 lampadaires sont impactés
5. Notifier les équipes terrain en priorité

---

## Règles générales de recommandation

- **Ne jamais proposer d'action automatique sans validation humaine**
- **Ne jamais modifier le dimming automatiquement**
- **Vérifier la LCU avant les lampadaires dans tous les cas de pannes multiples**
- **Baser les recommandations uniquement sur les données disponibles**
- **Signaler clairement l'absence de données si certaines mesures sont manquantes**
- **Prioriser les interventions selon la criticité (critique > élevé > moyen > faible)**
