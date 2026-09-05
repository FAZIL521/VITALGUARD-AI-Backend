from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from baseline.baseline import build_baseline
from risk.risk_engine import calculate_risk
from forecast.forecast import forecast_risk
from whatif.what_if import simulate, standard_scenarios
from explanation.explanation import human_explanation

app = FastAPI(title="VITALGUARD AI Risk Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VitalInput(BaseModel):
    timestamp: str
    heart_rate: float = Field(gt=20, lt=250)
    spo2: float = Field(gt=50, le=100)
    body_temperature: float = Field(gt=25, lt=45)
    ambient_temperature: float = Field(gt=-20, lt=70)
    humidity: float = Field(ge=0, le=100)
    activity_level: str
    rppg_quality: float = Field(default=0.0, ge=0, le=1)
    sensor_quality: float = Field(default=0.0, ge=0, le=1)

BASELINE_ROWS = [
    {"heart_rate":70,"spo2":98,"body_temperature":36.5,"activity_level":"resting"},
    {"heart_rate":72,"spo2":98,"body_temperature":36.6,"activity_level":"resting"},
    {"heart_rate":71,"spo2":99,"body_temperature":36.6,"activity_level":"resting"},
    {"heart_rate":74,"spo2":98,"body_temperature":36.7,"activity_level":"light"},
]
BASELINE = build_baseline(BASELINE_ROWS)

@app.get("/")
def root():
    return {"service":"VITALGUARD AI","status":"ready"}

@app.post("/baseline")
def baseline():
    return BASELINE

@app.post("/risk")
def risk(data: VitalInput):
    d = data.model_dump()
    result = calculate_risk(d, BASELINE, [])
    result["explanation"] = human_explanation(result)
    result.pop("feature_snapshot", None)
    return result

@app.post("/confidence")
def confidence(data: VitalInput):
    from confidence.confidence import calculate_confidence
    return {"confidence": calculate_confidence(data.model_dump())}

@app.post("/forecast")
def forecast(data: VitalInput):
    result = calculate_risk(data.model_dump(), BASELINE, [])
    return {"current_risk": result["risk_score"], "forecast": forecast_risk(result["risk_score"], [])}

class WhatIfRequest(BaseModel):
    data: VitalInput
    changes: Dict[str, Any] = {}

@app.post("/what-if")
def what_if(req: WhatIfRequest):
    d = req.data.model_dump()
    return simulate(d, BASELINE, [], req.changes)

@app.post("/what-if/standard")
def what_if_standard(data: VitalInput):
    return standard_scenarios(data.model_dump(), BASELINE, [])


# =========================================================
# LIVE DATA FOR MEMBER 3 UI
# =========================================================

LIVE_DATA = {
    "timestamp": "2026-09-04T15:00:00",
    "heart_rate": 104,
    "spo2": 95,
    "body_temperature": 37.2,
    "ambient_temperature": 36,
    "humidity": 75,
    "activity_level": "walking",
    "rppg_quality": 0.80,
    "sensor_quality": 0.87
}


@app.get("/api/live")
def api_live():

    current = LIVE_DATA.copy()

    # Run the existing VITALGUARD risk engine
    risk_result = calculate_risk(
        current,
        BASELINE,
        []
    )

    explanation = human_explanation(risk_result)

    # Forecast
    forecast_result = forecast_risk(
        risk_result["risk_score"],
        []
    )

    # Simple prototype heat indicator
    heat_index = (
        current["ambient_temperature"]
        + 0.05 * max(
            current["humidity"] - 40,
            0
        )
    )

    return {
        "available": True,

        "timestamp": current["timestamp"],

        "environment": {
            "temperature": current["ambient_temperature"],
            "humidity": current["humidity"],
            "heat_index": round(heat_index, 1),
            "available": True,
            "source": "DEMO"
        },

        "rppg": {
            "heart_rate": current["heart_rate"],
            "quality": current["rppg_quality"],
            "available": True
        },

        "vitals": {
            "heart_rate": current["heart_rate"],
            "spo2": current["spo2"],
            "body_temperature": current["body_temperature"],
            "activity_level": current["activity_level"]
        },

        "hardware": {
            "esp32_connected": False,
            "rppg_connected": True,
            "fusion_available": True
        },

        "risk": {
            "score": risk_result["risk_score"],
            "level": risk_result["risk_level"],
            "confidence": round(
                risk_result["confidence"] * 100,
                1
            ),
            "reasons": risk_result["reasons"],
            "explanation": explanation
        },

        "forecast": {
            "points": forecast_result
        },

        "recommendations": risk_result[
            "recommended_actions"
        ],

        "data_source": "SIMULATED_DEMO"
    }


# UI compatibility endpoints

@app.get("/live")
def live():
    return api_live()


@app.get("/status")
def status():
    return {
        "status": "online",
        "backend": "VITALGUARD AI",
        "risk_engine": "active"
    }


@app.get("/api/status")
def api_status():
    return {
        "status": "online",
        "backend": "VITALGUARD AI",
        "risk_engine": "active"
    }