from typing import Dict, Any

def calculate_confidence(data: Dict[str, Any]) -> float:
    rppg = max(0.0, min(1.0, float(data.get("rppg_quality", 0.0))))
    sensor = max(0.0, min(1.0, float(data.get("sensor_quality", 0.0))))

    # Conservative engineering score, not a probability of correctness.
    confidence = 0.5 * rppg + 0.5 * sensor

    # Penalize clearly missing/invalid quality indicators.
    required = ["heart_rate", "spo2", "body_temperature", "ambient_temperature", "humidity", "activity_level"]
    missing = sum(1 for k in required if k not in data)
    confidence *= max(0.0, 1.0 - 0.12 * missing)

    return round(max(0.0, min(1.0, confidence)), 3)
