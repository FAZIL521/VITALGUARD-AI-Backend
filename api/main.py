from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from baseline.baseline import build_baseline
from risk.risk_engine import calculate_risk
from forecast.forecast import forecast_risk
from whatif.what_if import simulate, standard_scenarios
from explanation.explanation import human_explanation


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
    changes: Dict[str, Any] = {}


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
# DEFAULT / DEMO SENSOR DATA
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
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "service": "VITALGUARD AI",
        "status": "ready",
        "message": "VITALGUARD AI backend is working"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

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

    global LATEST_SENSOR_DATA

    # Store the newest sensor reading in memory
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
def api_live():

    # Always use the latest data received from /api/sensor
    current = LATEST_SENSOR_DATA.copy()


    # --------------------------------------------------------
    # Risk calculation
    # --------------------------------------------------------

    try:
        risk_result = calculate_risk(
            current,
            BASELINE
        )
    except TypeError:
        risk_result = calculate_risk(
            current,
            BASELINE,
            []
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
            "Risk is calculated using personal baseline, "
            "vital deviations, environmental conditions, "
            "activity and signal quality."
        )


    # Add explanation without destroying the original result
    risk_result["explanation"] = explanation


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

        score = risk_result.get(
            "score",
            risk_result.get("risk_score", 0)
        )

        forecast_result = {
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


    # --------------------------------------------------------
    # Environmental heat indicator
    # --------------------------------------------------------

    temperature = current["ambient_temperature"]
    humidity = current["humidity"]

    heat_index = round(
        temperature + (humidity / 100) * 2.4,
        1
    )


    # --------------------------------------------------------
    # Determine whether data is demo data
    # --------------------------------------------------------

    is_demo = (
        current.get("timestamp") == LIVE_DATA["timestamp"]
        and current.get("heart_rate") == LIVE_DATA["heart_rate"]
        and current.get("ambient_temperature") == LIVE_DATA["ambient_temperature"]
        and current.get("humidity") == LIVE_DATA["humidity"]
    )


    if is_demo:
        data_source = "SIMULATED_DEMO"
        esp32_connected = False
    else:
        data_source = "EXTERNAL_SENSOR"
        esp32_connected = True


    # --------------------------------------------------------
    # rPPG status
    # --------------------------------------------------------

    rppg_available = (
        current.get("rppg_quality", 0) > 0
    )


    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    signal_confidence = round(
        (
            current.get("rppg_quality", 0)
            +
            current.get("sensor_quality", 0)
        ) / 2,
        3
    )


    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    recommendations = [
        "Reduce physical activity",
        "Move to a cooler environment",
        "Drink water",
        "Recheck vitals"
    ]


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
            "quality": current.get("rppg_quality", 0),
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

        "confidence": {
            "score": signal_confidence
        },

        "forecast": forecast_result,

        "recommendations": recommendations,

        "data_source": data_source
    }


# ============================================================
# ALTERNATIVE LIVE ENDPOINTS
# ============================================================

@app.get("/live")
def live_alias():
    return api_live()


@app.get("/status")
def status_alias():
    return api_live()


@app.get("/api/status")
def api_status_alias():
    return api_live()


# ============================================================
# BASELINE ENDPOINT
# ============================================================

@app.get("/baseline")
def get_baseline():
    return {
        "baseline": BASELINE
    }


# ============================================================
# RISK ENDPOINT
# ============================================================

@app.post("/risk")
def risk_endpoint(data: VitalInput):

    current = data.model_dump()

    try:
        result = calculate_risk(
            current,
            BASELINE
        )
    except TypeError:
        result = calculate_risk(
            current,
            BASELINE,
            []
        )

    try:
        result["explanation"] = human_explanation(result)
    except Exception:
        pass

    return result


# ============================================================
# CONFIDENCE ENDPOINT
# ============================================================

@app.post("/confidence")
def confidence_endpoint(data: VitalInput):

    quality = (
        data.rppg_quality
        +
        data.sensor_quality
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

    current = data.model_dump()

    try:
        return forecast_risk(
            current,
            BASELINE,
            []
        )

    except Exception:

        try:
            risk_result = calculate_risk(
                current,
                BASELINE
            )
        except TypeError:
            risk_result = calculate_risk(
                current,
                BASELINE,
                []
            )

        score = risk_result.get(
            "score",
            risk_result.get("risk_score", 0)
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
    data: VitalInput
):

    current = data.model_dump()

    try:
        return standard_scenarios(
            current,
            BASELINE,
            []
        )

    except Exception:

        return {
            "message": "Standard what-if scenarios unavailable"
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
    print(" POST /confidence")
    print(" POST /forecast")
    print(" POST /whatif")
    print(" POST /what-if")
    print(" GET  /baseline")
    print("=" * 60)
    print("")