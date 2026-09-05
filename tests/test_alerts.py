import os

os.environ["ALERTS_ENABLED"] = "false"

from api.main import dispatch_alert

def test_alert_below_threshold_does_not_trigger():
    data = {
        "heart_rate": 70,
        "spo2": 98,
        "body_temperature": 36.5,
        "ambient_temperature": 25,
        "humidity": 40,
        "activity_level": "resting",
        "rppg_quality": 0.9,
        "sensor_quality": 0.9,
        "timestamp": "2026-01-01T00:00:00",
    }
    risk = {"risk_score": 20, "risk_level": "LOW", "confidence": 0.9}
    result = dispatch_alert(data, risk)
    assert result["triggered"] is False
