from typing import Dict, Any, List

def forecast_risk(current_score: float, history: List[Dict[str, Any]] | None = None):
    history = history or []
    scores = [float(x.get("risk_score", current_score)) for x in history[-5:]]
    scores.append(float(current_score))
    if len(scores) >= 2:
        slope = (scores[-1] - scores[0]) / max(1, len(scores)-1)
    else:
        slope = 0.0

    out = []
    for minutes in (10, 20, 30):
        # Simple transparent short-term trajectory extrapolation.
        projected = max(0.0, min(100.0, current_score + slope * (minutes / 5.0)))
        out.append({"minutes": minutes, "risk": round(projected, 1)})
    return out
