from typing import Dict, Any, List

def _z(value: float, stats: Dict[str, float]) -> float:
    return (float(value) - stats["mean"]) / max(stats["std"], 1e-6)

def linear_slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    xmean = (n - 1) / 2
    ymean = sum(values) / n
    denom = sum((i-xmean)**2 for i in range(n))
    return sum((i-xmean)*(y-ymean) for i,y in enumerate(values)) / denom if denom else 0.0

def make_features(current: Dict[str, Any], baseline: Dict[str, Any], history: List[Dict[str, Any]] | None = None):
    history = history or []
    hrs = [float(x["heart_rate"]) for x in history[-6:]] + [float(current["heart_rate"])]
    temps = [float(x["body_temperature"]) for x in history[-6:]] + [float(current["body_temperature"])]
    spo2s = [float(x["spo2"]) for x in history[-6:]] + [float(current["spo2"])]

    return {
        "hr_deviation_z": _z(current["heart_rate"], baseline["heart_rate"]),
        "spo2_deviation_z": _z(current["spo2"], baseline["spo2"]),
        "temperature_deviation_z": _z(current["body_temperature"], baseline["body_temperature"]),
        "hr_slope": linear_slope(hrs),
        "spo2_slope": linear_slope(spo2s),
        "temperature_slope": linear_slope(temps),
        "ambient_temperature": float(current["ambient_temperature"]),
        "humidity": float(current["humidity"]),
        "activity_level": str(current["activity_level"]).lower(),
        "rppg_quality": float(current.get("rppg_quality", 0.0)),
        "sensor_quality": float(current.get("sensor_quality", 0.0)),
    }
