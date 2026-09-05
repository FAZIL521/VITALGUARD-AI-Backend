import json
from baseline.baseline import build_baseline
from risk.risk_engine import calculate_risk
from forecast.forecast import forecast_risk
from whatif.what_if import standard_scenarios
from explanation.explanation import human_explanation

baseline_rows = [
    {"heart_rate":70,"spo2":98,"body_temperature":36.5,"activity_level":"resting"},
    {"heart_rate":72,"spo2":98,"body_temperature":36.6,"activity_level":"resting"},
    {"heart_rate":71,"spo2":99,"body_temperature":36.6,"activity_level":"resting"},
    {"heart_rate":74,"spo2":98,"body_temperature":36.7,"activity_level":"light"},
]
baseline = build_baseline(baseline_rows)

data = {
    "timestamp":"2026-08-31T12:20:00",
    "heart_rate":104,
    "spo2":95,
    "body_temperature":37.2,
    "ambient_temperature":36,
    "humidity":75,
    "activity_level":"walking",
    "rppg_quality":0.80,
    "sensor_quality":0.87,
}

result = calculate_risk(data, baseline, [])
output = {
    "risk_score": result["risk_score"],
    "risk_level": result["risk_level"],
    "confidence": result["confidence"],
    "reasons": result["reasons"],
    "forecast": forecast_risk(result["risk_score"], []),
    "recommended_actions": result["recommended_actions"],
    "explanation": human_explanation(result),
    "what_if": standard_scenarios(data, baseline, [])
}
print(json.dumps(output, indent=2))
