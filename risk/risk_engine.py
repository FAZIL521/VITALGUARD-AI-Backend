from typing import Dict, Any, List
from features.feature_engineering import make_features
from confidence.confidence import calculate_confidence

def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def _component_from_abs_z(z: float, scale=20.0):
    return _clamp(abs(z) * scale)

def calculate_risk(data: Dict[str, Any], baseline: Dict[str, Any], history: List[Dict[str, Any]] | None = None):
    f = make_features(data, baseline, history)

    hr_risk = _component_from_abs_z(f["hr_deviation_z"])
    # For SpO2, lower than baseline is more concerning; positive deviation is not penalized.
    spo2_low_z = max(0.0, -f["spo2_deviation_z"])
    spo2_risk = _clamp(spo2_low_z * 25.0)

    temp_risk = _clamp(max(0.0, f["temperature_deviation_z"]) * 25.0)

    env_heat = max(0.0, (f["ambient_temperature"] - 30.0) * 8.0)
    humidity = max(0.0, (f["humidity"] - 60.0) * 0.7)
    environment_risk = _clamp(env_heat + humidity)

    trend_risk = _clamp(
        max(0.0, f["hr_slope"]) * 3.0 +
        max(0.0, f["temperature_slope"]) * 25.0 +
        max(0.0, -f["spo2_slope"]) * 12.0
    )

    # Activity adjustment: elevated HR while active is less anomalous than at rest.
    activity = f["activity_level"]
    if activity in ("walking", "light", "moderate"):
        hr_risk *= 0.75
    elif activity in ("running", "vigorous", "high"):
        hr_risk *= 0.55

    raw = (
        0.25 * hr_risk +
        0.20 * spo2_risk +
        0.25 * temp_risk +
        0.15 * environment_risk +
        0.15 * trend_risk
    )
    score = round(_clamp(raw), 1)

    if score < 30:
        level = "LOW"
    elif score < 60:
        level = "MODERATE"
    elif score < 80:
        level = "HIGH"
    else:
        level = "CRITICAL"

    confidence = calculate_confidence(data)

    components = {
        "hr_deviation": round(0.25 * hr_risk, 1),
        "spo2_deviation": round(0.20 * spo2_risk, 1),
        "temperature_deviation": round(0.25 * temp_risk, 1),
        "environment": round(0.15 * environment_risk, 1),
        "trend": round(0.15 * trend_risk, 1),
    }

    reasons = []
    if components["hr_deviation"] > 0:
        reasons.append({"factor":"hr_deviation","direction":"up" if f["hr_deviation_z"] > 0 else "down","contribution":components["hr_deviation"]})
    if components["spo2_deviation"] > 0:
        reasons.append({"factor":"spo2_deviation","direction":"down","contribution":components["spo2_deviation"]})
    if components["temperature_deviation"] > 0:
        reasons.append({"factor":"temperature_deviation","direction":"up","contribution":components["temperature_deviation"]})
    if components["environment"] > 0:
        reasons.append({"factor":"heat_humidity","direction":"up","contribution":components["environment"]})
    if components["trend"] > 0:
        reasons.append({"factor":"worsening_trend","direction":"up","contribution":components["trend"]})

    reasons.sort(key=lambda x: x["contribution"], reverse=True)

    actions = []
    if level in ("HIGH", "CRITICAL"):
        actions = ["Reduce physical activity", "Move to a cooler environment", "Drink water", "Recheck vitals"]
    elif level == "MODERATE":
        actions = ["Take a short rest", "Monitor hydration", "Recheck vitals soon"]
    else:
        actions = ["Continue normal monitoring"]

    return {
        "risk_score": score,
        "risk_level": level,
        "confidence": confidence,
        "reasons": reasons,
        "recommended_actions": actions,
        "feature_snapshot": f,
    }
