from copy import deepcopy
from risk.risk_engine import calculate_risk

def simulate(data, baseline, history=None, changes=None):
    changes = changes or {}
    modified = deepcopy(data)
    modified.update(changes)
    result = calculate_risk(modified, baseline, history)
    return {
        "changes": changes,
        "predicted_risk": result["risk_score"],
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
    }

def standard_scenarios(data, baseline, history=None):
    scenarios = {
        "rest": {"activity_level": "resting"},
        "cool_environment": {"ambient_temperature": max(20.0, float(data["ambient_temperature"]) - 6.0)},
    }
    return {name: simulate(data, baseline, history, changes) for name, changes in scenarios.items()}
