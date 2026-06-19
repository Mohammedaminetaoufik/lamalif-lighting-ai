"""Standalone tests for the rule engine — pure Python, no DB, no LLM.

Run:  venv/Scripts/python.exe scripts/test_recommendation_engine.py
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendations import (  # noqa: E402
    evaluate_lampadaire, evaluate_lcu, evaluate_page, evaluate_daily,
)
from app.recommendations.scoring import (  # noqa: E402
    compute_lampadaire_maintainability_score,
)
from app.recommendations.zone_rules import evaluate_row as zone_row  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL  {name}")


def hours_ago(h):
    return (datetime.now(tz=timezone.utc) - timedelta(hours=h)).isoformat()


def priorities(result):
    return {r.priority for r in result["recommendations"]}


print("Zone rules")
check("zone 100% offline -> critical",
      zone_row({"zone": "Rabat", "total_lampadaires": 19, "offline_count": 19})[0].priority == "critical")
check("zone 50% offline -> high",
      zone_row({"zone": "Z", "total_lampadaires": 10, "offline_count": 5})[0].priority == "high")
check("zone 1/10 offline -> medium",
      zone_row({"zone": "Z", "total_lampadaires": 10, "offline_count": 1})[0].priority == "medium")
check("zone 0 offline -> no rec",
      zone_row({"zone": "Z", "total_lampadaires": 10, "offline_count": 0}) == [])

print("LCU rules")
lcu_crit = evaluate_lcu({"details": {"reference": "LCU-1", "status": "online", "lampadaires_count": 10, "offline_count": 1},
                         "health": {"health_score": 25}, "lamps": [], "alerts": []})
check("LCU health<30 -> critical present", "critical" in priorities(lcu_crit))
check("LCU risk_score computed", isinstance(lcu_crit["scores"]["risk_score"], int))

print("Lampadaire rules")
offline = evaluate_lampadaire({"details": {"reference": "LP-1", "etat": "offline", "lcu_reference": "LCU-1",
                                           "latitude": 1, "longitude": 1, "zone": "Z",
                                           "commissioning_status": "commissioned"},
                               "diagnostics": {"last_measure_at": hours_ago(1)}, "alerts": [], "workorders": []})
check("lampadaire offline -> high", "high" in priorities(offline) or "critical" in priorities(offline))

offline_crit = evaluate_lampadaire({"details": {"reference": "LP-2", "etat": "offline", "lcu_reference": "LCU-1",
                                                "latitude": 1, "longitude": 1, "zone": "Z",
                                                "commissioning_status": "commissioned"},
                                    "diagnostics": {"critical_alerts_count": 2, "last_measure_at": hours_ago(1)},
                                    "alerts": [{"severity": "critical"}], "workorders": []})
check("lampadaire offline + alerte critique -> critical", "critical" in priorities(offline_crit))

print("Driver rules")
hot = evaluate_lampadaire({"details": {"reference": "LP-3", "etat": "online", "lcu_reference": "LCU-1",
                                       "latitude": 1, "longitude": 1, "zone": "Z",
                                       "commissioning_status": "commissioned"},
                           "diagnostics": {"driver_temperature": 85, "last_measure_at": hours_ago(1)},
                           "alerts": [], "workorders": []})
check("driver temp>=80 -> critical", "critical" in priorities(hot))

print("Maintenance rules")
old_wo = evaluate_lampadaire({"details": {"reference": "LP-4", "etat": "online", "lcu_reference": "LCU-1",
                                          "latitude": 1, "longitude": 1, "zone": "Z",
                                          "commissioning_status": "commissioned"},
                              "diagnostics": {"last_measure_at": hours_ago(1)},
                              "alerts": [],
                              "workorders": [{"title": "Remplacer driver", "status": "in_progress",
                                              "priority": "high", "created_at": hours_ago(60)}]})
check("work order >48h -> high", "high" in priorities(old_wo))

print("Maintainability score")
full = {"details": {"reference": "LP-5", "etat": "online", "lcu_reference": "LCU-1",
                    "latitude": 1, "longitude": 1, "zone": "Z", "lcu_id": 1,
                    "commissioning_status": "commissioned"},
        "diagnostics": {"last_measure_at": hours_ago(1)}, "alerts": [], "workorders": []}
no_gps = {**full, "details": {**full["details"], "latitude": None, "longitude": None}}
no_lcu = {**full, "details": {**full["details"], "lcu_id": None, "lcu_reference": None}}
check("no GPS lowers maintainability",
      compute_lampadaire_maintainability_score(no_gps) < compute_lampadaire_maintainability_score(full))
check("no LCU lowers maintainability",
      compute_lampadaire_maintainability_score(no_lcu) < compute_lampadaire_maintainability_score(full))

print("Daily / page (no LLM needed)")
daily = evaluate_daily({"critical_alerts": 3, "offline_lampadaires": 20, "total_lampadaires": 100},
                       {"zone_health": [{"zone": "Rabat", "total_lampadaires": 19, "offline_count": 19}]})
check("daily returns recommendations without LLM", len(daily) > 0)
check("daily critical alerts -> critical rec present", any(r.priority == "critical" for r in daily))

dash = evaluate_page("dashboard", {"top_zones": [{"zone": "Rabat", "total_lampadaires": 19, "offline_count": 19}],
                                   "critical_lcus": [{"reference": "LCU-9", "health_score": 20}],
                                   "oldest_workorders": [{"title": "WO", "status": "open", "priority": "critical",
                                                          "age_hours": 50, "id": 1}]})
check("page dashboard returns recommendations", len(dash) > 0)

print()
print(f"RESULT: {_PASS} passed, {_FAIL} failed")
sys.exit(1 if _FAIL else 0)
