def generate_basic_summary(question: str, rows: list[dict]) -> str:
    count = len(rows)
    if count == 0:
        return "Aucun résultat trouvé pour cette requête."
    return f"La requête a retourné {count} résultat(s)."


def rule_based_recommendation(question: str, rows: list[dict]) -> str:
    q = question.lower()

    if any(k in q for k in ("hors ligne", "offline")):
        return (
            "Vérifiez les LCUs associées aux lampadaires hors ligne avant de créer "
            "plusieurs interventions. Une LCU défaillante peut expliquer plusieurs pannes simultanées."
        )
    if any(k in q for k in ("alerte", "critique", "alert")):
        return (
            "Priorisez les alertes critiques et assurez-vous que les bons de travail correspondants "
            "sont créés et assignés rapidement."
        )
    if any(k in q for k in ("consommation", "énergie", "energie", "puissance", "kwh")):
        return (
            "Analysez les profils de dimming des zones les plus consommatrices. "
            "Toute modification de profil doit faire l'objet d'une validation humaine."
        )
    if any(k in q for k in ("bon de travail", "intervention", "workorder", "technicien")):
        return (
            "Traitez en priorité les bons de travail anciens ou de priorité critique "
            "afin d'éviter les dépassements de délai d'intervention."
        )
    if any(k in q for k in ("télémétrie", "telemetrie", "mesure")):
        return (
            "Vérifiez la communication avec les LCUs concernées et l'état des capteurs associés. "
            "Une absence de télémétrie peut indiquer un problème réseau ou matériel."
        )
    if any(k in q for k in ("commissioning", "mise en service", "déploiement")):
        return (
            "Finalisez les tests de commissioning (comm, dimming, metering) avant mise en production. "
            "Un lampadaire non validé terrain ne doit pas être considéré opérationnel."
        )
    if any(k in q for k in ("driver", "température", "temperature", "surchauffe", "thermique")):
        return (
            "Un driver LED dont la température dépasse 70 °C présente un risque de défaillance. "
            "Planifiez une inspection physique et vérifiez la ventilation de l'armoire."
        )
    if any(k in q for k in ("contrôleur", "controleur", "signal", "réseau", "firmware")):
        return (
            "Un signal faible ou un firmware obsolète peut perturber la remontée de données. "
            "Priorisez les mises à jour terrain et vérifiez les antennes des contrôleurs concernés."
        )
    if any(k in q for k in ("zone critique", "zone", "priorité", "maintenance")):
        return (
            "Concentrez les ressources terrain sur les zones affichant un taux de pannes ou "
            "d'alertes critiques supérieur à la moyenne. Revoyez les cycles de maintenance préventive."
        )
    if any(k in q for k in ("dimming", "intensité", "d4i", "dali")):
        return (
            "Vérifiez la compatibilité du protocole de dimming (DALI, D4i, 0-10V) avant toute "
            "modification de profil. Un mauvais protocole peut endommager les drivers."
        )
    if any(k in q for k in ("kpi", "global", "situation", "résumé", "réseau")):
        return (
            "Utilisez les KPIs globaux pour identifier les tendances à l'échelle du réseau. "
            "Des écarts entre zones indiquent des besoins de rééquilibrage des équipes terrain."
        )

    return (
        "Consultez régulièrement les tableaux de bord Smart Lighting pour anticiper "
        "les pannes et optimiser la maintenance préventive du réseau d'éclairage."
    )


def infer_chart_type(columns: list[str], rows: list[dict]) -> dict:
    if not rows:
        return {"type": "table", "x": None, "y": None}

    if len(columns) == 2:
        sample = rows[0].get(columns[1])
        if isinstance(sample, (int, float)):
            return {"type": "bar", "x": columns[0], "y": columns[1]}

    return {"type": "table", "x": None, "y": None}
