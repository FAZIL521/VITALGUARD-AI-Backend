from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable, Dict, Any

@dataclass(frozen=True)
class BaselineStats:
    mean: float
    std: float
    minimum: float
    maximum: float

def _stats(values: Iterable[float]) -> BaselineStats:
    xs = [float(x) for x in values]
    if not xs:
        raise ValueError("At least one value is required.")
    mu = mean(xs)
    sd = pstdev(xs) if len(xs) > 1 else 1.0
    return BaselineStats(mu, max(sd, 1e-6), min(xs), max(xs))

def build_baseline(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(rows)
    resting = [
        r for r in rows
        if str(r.get("activity_level", "")).lower() in ("resting", "light")
    ]

    # Prefer resting/light observations for the initial personal baseline.
    # Fall back to all observations if there are fewer than 3 such observations.
    source = resting if len(resting) >= 3 else rows

    return {
        "sample_count": len(source),
        "source": "resting_light" if source is resting else "all_available",
        "heart_rate": _stats([r["heart_rate"] for r in source]).__dict__,
        "spo2": _stats([r["spo2"] for r in source]).__dict__,
        "body_temperature": _stats([r["body_temperature"] for r in source]).__dict__,
    }
