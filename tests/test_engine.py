from baseline.baseline import build_baseline
from risk.risk_engine import calculate_risk

BASE = build_baseline([
    {"heart_rate":70,"spo2":98,"body_temperature":36.5,"activity_level":"resting"},
    {"heart_rate":72,"spo2":98,"body_temperature":36.6,"activity_level":"resting"},
    {"heart_rate":71,"spo2":99,"body_temperature":36.6,"activity_level":"resting"},
])

DATA = {
    "timestamp":"2026-08-31T12:20:00",
    "heart_rate":90,"spo2":97,"body_temperature":36.9,
    "ambient_temperature":34,"humidity":70,"activity_level":"walking",
    "rppg_quality":0.9,"sensor_quality":0.9
}

def test_deterministic():
    assert calculate_risk(DATA, BASE, []) == calculate_risk(DATA, BASE, [])

def test_output_range():
    r = calculate_risk(DATA, BASE, [])
    assert 0 <= r["risk_score"] <= 100
    assert 0 <= r["confidence"] <= 1

def test_heat_increases_risk():
    cool = dict(DATA, ambient_temperature=25, humidity=40)
    hot = dict(DATA, ambient_temperature=40, humidity=90)
    assert calculate_risk(hot, BASE, [])["risk_score"] >= calculate_risk(cool, BASE, [])["risk_score"]
