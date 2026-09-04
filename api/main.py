from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime

from risk.risk_engine import calculate_risk
from explanation.explanation import human_explanation
from forecast.forecast import forecast_risk
from whatif.whatif_engine import simulate
from baseline.baseline import build_baseline


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="VITALGUARD AI Risk Engine",
    description="Personalized heat-risk and health monitoring backend",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://vitalguard-ui.onrender.com"
],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATA MODEL
# ============================================================

class VitalInput(BaseModel):
    timestamp: str

    heart_rate: float = Field(
        gt=20,
        lt=250
    )

    spo2: float = Field(
        gt=50,
        le=100
    )

    body_temperature: float = Field(
        gt=25,
        lt=45
    )

    ambient_temperature: float = Field(
        gt=-20,
        lt=70
    )

    humidity: float = Field(
        ge=0,
        le=100
    )

    activity_level: str

    rppg_quality: float = Field(
        default=0.0,
        ge=0,
        le=1
    )

    sensor_quality: float = Field(
        default=0.0,
        ge=0,
        le=1
    )


class WhatIfRequest(BaseModel):
    data: VitalInput
    changes: Dict[str, Any]


# ============================================================
# PERSONAL BASELINE
# ============================================================

BASELINE_ROWS = [
    {
        "heart_rate": 70,
        "spo2": 98,
        "body_temperature": 36.5,
        "activity_level": "resting"
    },
    {
        "heart_rate": 72,
        "spo2": 98,
        "body_temperature": 36.6,
        "activity_level": "resting"
    },
    {
        "heart_rate": 71,
        "spo2": 99,
        "body_temperature": 36.6,
        "activity_level": "resting"
    },
    {
        "heart_rate": 74,
        "spo2": 98,
        "body_temperature": 36.7,
        "activity_level": "light"
    }
]

BASELINE = build_baseline(BASELINE_ROWS)


# ============================================================
# DEMO DATA
# ============================================================

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


# ============================================================
# LATEST SENSOR DATA
# ============================================================

LATEST_SENSOR_DATA = LIVE_DATA.copy()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "project": "VITALGUARD",
        "status": "running",
        "message": "VITALGUARD AI backend is working"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# SENSOR INPUT
# ============================================================

@app.post("/api/sensor")
def receive_sensor_data(data: VitalInput):
    """
    Receive live data from ESP32 / rPPG / sensor gateway.
    The latest reading is stored in memory.
    """

    global LATEST_SENSOR_DATA

    LATEST_SENSOR_DATA = data.model_dump()

    return {
        "success": True,
        "message": "Sensor data received successfully",
        "data": LATEST_SENSOR_DATA
    }


# ============================================================
# LIVE DATA
# ============================================================

@app.get("/api/live")
def get_live_data():

    current = LATEST_SENSOR_DATA.copy()

    # --------------------------------------------------------
    # Risk calculation
    # --------------------------------------------------------

    risk_result = calculate_risk(
        current,
        BASELINE
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    try:
        explanation = human_explanation(
            risk_result
        )
    except Exception:
        explanation = (
            "Risk is calculated from personal baseline, "
            "vital deviations, environmental conditions "
            "and signal quality."
        )

    # --------------------------------------------------------
    # Forecast
    # --------------------------------------------------------

    try:
        forecast_result = forecast_risk(
            current,
            BASELINE,
            []
        )
    except Exception:
        forecast_result = {
            "points": [
                {
                    "minutes": 10,
                    "risk": risk_result.get("score", 0)
                },
                {
                    "minutes": 20,
                    "risk": risk_result.get("score", 0)
                },
                {
                    "minutes": 30,
                    "risk": risk_result.get("score", 0)
                }
            ]
        }

    # --------------------------------------------------------
    # Simple heat indicator
    # --------------------------------------------------------

    temperature = current["ambient_temperature"]
    humidity = current["humidity"]

    heat_index = round(
        temperature
        + (humidity / 100) * 2.4,
        1
    )

    # --------------------------------------------------------
    # Determine source
    # --------------------------------------------------------

    is_demo = current == LIVE_DATA

    if is_demo:
        data_source = "SIMULATED_DEMO"
        esp32_connected = False
    else:
        data_source = "EXTERNAL_SENSOR"
        esp32_connected = True

    # --------------------------------------------------------
    # rPPG
    # --------------------------------------------------------

    rppg_available = current.get(
        "rppg_quality",
        0
    ) > 0

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return {
        "available": True,

        "timestamp": current["timestamp"],

        "environment": {
            "temperature": temperature,
            "humidity": humidity,
            "heat_index": heat_index,
            "available": True,
            "source": (
                "DEMO"
                if is_demo
                else "ESP32+DHT11"
            )
        },

        "rppg": {
            "heart_rate": current["heart_rate"],
            "quality": current["rppg_quality"],
            "available": rppg_available
        },

        "vitals": {
            "heart_rate": current["heart_rate"],
            "spo2": current["spo2"],
            "body_temperature": current["body_temperature"],
            "activity_level": current["activity_level"]
        },

        "hardware": {
            "esp32_connected": esp32_connected,
            "rppg_connected": rppg_available,
            "fusion_available": True
        },

        "risk": risk_result,

        "forecast": forecast_result,

        "recommendations": [
            "Reduce physical activity",
            "Move to a cooler environment",
            "Drink water",
            "Recheck vitals"
        ],

        "data_source": data_source
    }


# ============================================================
# ALTERNATIVE LIVE ENDPOINTS
# ============================================================

@app.get("/live")
def live_alias():
    return get_live_data()


@app.get("/status")
def status_alias():
    return get_live_data()


@app.get("/api/status")
def api_status_alias():
    return get_live_data()


# ============================================================
# RISK ENDPOINT
# ============================================================

@app.post("/risk")
def risk_endpoint(data: VitalInput):

    result = calculate_risk(
        data.model_dump(),
        BASELINE
    )

    return result


# ============================================================
# CONFIDENCE ENDPOINT
# ============================================================

@app.post("/confidence")
def confidence_endpoint(data: VitalInput):

    quality = (
        data.rppg_quality
        + data.sensor_quality
    ) / 2

    return {
        "confidence": round(
            quality * 100,
            1
        )
    }


# ============================================================
# FORECAST ENDPOINT
# ============================================================

@app.post("/forecast")
def forecast_endpoint(data: VitalInput):

    try:
        return forecast_risk(
            data.model_dump(),
            BASELINE,
            []
        )
    except Exception:
        risk = calculate_risk(
            data.model_dump(),
            BASELINE
        )

        score = risk.get(
            "score",
            0
        )

        return {
            "points": [
                {
                    "minutes": 10,
                    "risk": score
                },
                {
                    "minutes": 20,
                    "risk": score
                },
                {
                    "minutes": 30,
                    "risk": score
                }
            ]
        }


# ============================================================
# WHAT-IF
# ============================================================

@app.post("/what-if")
def what_if_endpoint(
    req: WhatIfRequest
):

    current = req.data.model_dump()

    return simulate(
        current,
        BASELINE,
        [],
        req.changes
    )


# ============================================================
# WHAT-IF COMPATIBILITY ENDPOINT
# ============================================================

@app.post("/whatif")
def whatif_endpoint(
    req: WhatIfRequest
):

    current = req.data.model_dump()

    return simulate(
        current,
        BASELINE,
        [],
        req.changes
    )


# ============================================================
# STANDARD WHAT-IF
# ============================================================

@app.post("/what-if/standard")
def standard_what_if(
    req: WhatIfRequest
):

    current = req.data.model_dump()

    return simulate(
        current,
        BASELINE,
        [],
        req.changes
    )


# ============================================================
# BASELINE
# ============================================================

@app.get("/baseline")
def get_baseline():

    return {
        "baseline": BASELINE
    }


# ============================================================
# STARTUP MESSAGE
# ============================================================

@app.on_event("startup")
def startup_event():

    print("")
    print("=" * 60)
    print(" VITALGUARD AI BACKEND")
    print("=" * 60)
    print(" Backend: http://127.0.0.1:8000")
    print(" Swagger: http://127.0.0.1:8000/docs")
    print("")
    print(" Available endpoints:")
    print(" POST /api/sensor")
    print(" GET  /api/live")
    print(" POST /risk")
    print(" POST /forecast")
    print(" POST /whatif")
    print("=" * 60)
    print("")