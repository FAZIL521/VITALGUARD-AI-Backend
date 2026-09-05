# ============================================================
# VITALGUARD AI BACKEND
# COMPLETE VERSION WITH EMERGENCY SMS + VOICE ALERTS
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime
import os
import time

# ------------------------------------------------------------
# VITALGUARD AI MODULES
# ------------------------------------------------------------

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
    description="Personalized heat-risk monitoring and emergency alert backend",
    version="2.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://vitalguard-ui.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INPUT MODEL
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


class AlertRequest(BaseModel):
    data: VitalInput

    channel: str = Field(
        default="auto",
        pattern="^(auto|sms|call)$"
    )


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
# DEMO SENSOR DATA
# ============================================================

LIVE_DATA = {
    "timestamp": "2026-09-05T15:00:00",

    "heart_rate": 104,

    "spo2": 95,

    "body_temperature": 37.2,

    "ambient_temperature": 36.0,

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
# ALERT CONFIGURATION
# ============================================================

ALERTS_ENABLED = (
    os.getenv("ALERTS_ENABLED", "false").lower()
    == "true"
)

EMERGENCY_CONTACT = os.getenv(
    "EMERGENCY_CONTACT",
    ""
)

EMERGENCY_CONTACT_2 = os.getenv(
    "EMERGENCY_CONTACT_2",
    ""
)

TWILIO_ACCOUNT_SID = os.getenv(
    "TWILIO_ACCOUNT_SID",
    ""
)

TWILIO_AUTH_TOKEN = os.getenv(
    "TWILIO_AUTH_TOKEN",
    ""
)

TWILIO_FROM_NUMBER = os.getenv(
    "TWILIO_FROM_NUMBER",
    ""
)

ALERT_CONFIDENCE_THRESHOLD = float(
    os.getenv(
        "ALERT_CONFIDENCE_THRESHOLD",
        "0.75"
    )
)

ALERT_COOLDOWN_SECONDS = int(
    os.getenv(
        "ALERT_COOLDOWN_SECONDS",
        "600"
    )
)

# ------------------------------------------------------------
# IMPORTANT:
#
# true  = Twilio Trial-compatible predefined template
#
# false = normal custom VITALGUARD SMS
#
# Keep TRUE while using Twilio Trial.
# Change to FALSE after upgrading Twilio.
# ------------------------------------------------------------

TWILIO_TRIAL_MODE = (
    os.getenv(
        "TWILIO_TRIAL_MODE",
        "true"
    ).lower()
    == "true"
)


# ============================================================
# ALERT MEMORY
# ============================================================

ALERT_HISTORY: List[Dict[str, Any]] = []

LAST_ALERT_TIME = {
    "sms": 0.0,
    "call": 0.0
}


# ============================================================
# OPTIONAL TWILIO IMPORT
# ============================================================

try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True

except ImportError:
    Client = None
    TWILIO_AVAILABLE = False


# ============================================================
# TWILIO STATUS
# ============================================================

def twilio_is_ready() -> bool:

    return (
        TWILIO_AVAILABLE
        and bool(TWILIO_ACCOUNT_SID)
        and bool(TWILIO_AUTH_TOKEN)
        and bool(TWILIO_FROM_NUMBER)
    )


# ============================================================
# SMS MESSAGE
# ============================================================

def format_alert_message(
    data: Dict[str, Any],
    risk_result: Dict[str, Any]
) -> str:

    score = risk_result.get(
        "risk_score",
        risk_result.get("score", 0)
    )

    level = risk_result.get(
        "risk_level",
        "UNKNOWN"
    )

    confidence = risk_result.get(
        "confidence",
        0
    )

    if isinstance(confidence, float):
        confidence_percent = round(
            confidence * 100,
            1
        )
    else:
        confidence_percent = confidence

    return (
        "VITALGUARD ALERT\n"
        f"Risk: {level}\n"
        f"Risk Score: {score}/100\n"
        f"Confidence: {confidence_percent}%\n"
        f"Heart Rate: {data.get('heart_rate')} BPM\n"
        f"SpO2: {data.get('spo2')}%\n"
        f"Body Temp: {data.get('body_temperature')} C\n"
        f"Ambient Temp: {data.get('ambient_temperature')} C\n"
        f"Humidity: {data.get('humidity')}%\n"
        f"Activity: {data.get('activity_level')}\n"
        "Please check the person's condition."
    )


# ============================================================
# VOICE MESSAGE
# ============================================================

def format_call_twiml(
    risk_result: Dict[str, Any]
) -> str:

    level = risk_result.get(
        "risk_level",
        "critical"
    )

    score = risk_result.get(
        "risk_score",
        risk_result.get("score", 0)
    )

    return f"""
<Response>
    <Say voice="alice">
        VITALGUARD emergency alert.
        The monitored person's health risk level is {level}.
        Current risk score is {score} out of 100.
        Please check the person immediately.
    </Say>
</Response>
""".strip()


# ============================================================
# SEND SMS
# ============================================================

def send_sms(
    to_number: str,
    message: str
) -> Dict[str, Any]:

    if not twilio_is_ready():

        return {
            "success": False,
            "mode": "not_configured",
            "error": (
                "Twilio is not configured. "
                "Check ALERTS_ENABLED, Account SID, "
                "Auth Token and From Number."
            )
        }

    try:

        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )

        # ----------------------------------------------------
        # TWILIO TRIAL MODE
        #
        # Trial accounts cannot send arbitrary SMS bodies.
        # They require a predefined template.
        # ----------------------------------------------------

        if TWILIO_TRIAL_MODE:

            msg = client.messages.create(
                body="sms_internal_alerts",
                from_=TWILIO_FROM_NUMBER,
                to=to_number
            )

            return {
                "success": True,
                "mode": "twilio_trial_template",
                "template": "sms_internal_alerts",
                "sid": msg.sid,
                "to": to_number
            }

        # ----------------------------------------------------
        # NORMAL / UPGRADED TWILIO ACCOUNT
        # ----------------------------------------------------

        msg = client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=to_number
        )

        return {
            "success": True,
            "mode": "twilio",
            "sid": msg.sid,
            "to": to_number
        }

    except Exception as exc:

        return {
            "success": False,
            "mode": "twilio",
            "to": to_number,
            "error": str(exc)
        }


# ============================================================
# MAKE VOICE CALL
# ============================================================

def make_call(
    to_number: str,
    risk_result: Dict[str, Any]
) -> Dict[str, Any]:

    if not twilio_is_ready():

        return {
            "success": False,
            "mode": "not_configured",
            "error": "Twilio is not configured."
        }

    try:

        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )

        twiml = format_call_twiml(
            risk_result
        )

        call = client.calls.create(
            twiml=twiml,
            from_=TWILIO_FROM_NUMBER,
            to=to_number
        )

        return {
            "success": True,
            "mode": "twilio",
            "sid": call.sid,
            "to": to_number
        }

    except Exception as exc:

        return {
            "success": False,
            "mode": "twilio",
            "to": to_number,
            "error": str(exc)
        }


# ============================================================
# RECORD ALERT
# ============================================================

def record_alert(
    kind: str,
    risk_result: Dict[str, Any],
    results: List[Dict[str, Any]]
):

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",

        "kind": kind,

        "risk_score": risk_result.get(
            "risk_score",
            risk_result.get("score", 0)
        ),

        "risk_level": risk_result.get(
            "risk_level",
            "UNKNOWN"
        ),

        "confidence": risk_result.get(
            "confidence",
            0
        ),

        "results": results
    }

    ALERT_HISTORY.append(record)

    # Keep only recent alerts
    if len(ALERT_HISTORY) > 100:
        del ALERT_HISTORY[:-100]

    return record


# ============================================================
# ALERT COOLDOWN
# ============================================================

def cooldown_available(
    channel: str
) -> bool:

    now = time.time()

    last_time = LAST_ALERT_TIME.get(
        channel,
        0
    )

    return (
        now - last_time
        >= ALERT_COOLDOWN_SECONDS
    )


def mark_alert_sent(
    channel: str
):

    LAST_ALERT_TIME[channel] = time.time()


# ============================================================
# DISPATCH ALERT
# ============================================================

def dispatch_alert(
    data: Dict[str, Any],
    risk_result: Dict[str, Any],
    channel: str = "auto"
) -> Dict[str, Any]:

    risk_level = str(
        risk_result.get(
            "risk_level",
            "LOW"
        )
    ).upper()

    confidence = float(
        risk_result.get(
            "confidence",
            0
        )
    )

    # --------------------------------------------------------
    # CONFIDENCE CHECK
    # --------------------------------------------------------

    if confidence < ALERT_CONFIDENCE_THRESHOLD:

        return {
            "triggered": False,
            "reason": (
                "Confidence below alert threshold."
            ),
            "confidence": confidence,
            "threshold": ALERT_CONFIDENCE_THRESHOLD
        }

    # --------------------------------------------------------
    # ONLY HIGH / CRITICAL SHOULD ESCALATE
    # --------------------------------------------------------

    if channel == "auto":

        if risk_level == "CRITICAL":
            selected_channel = "critical"

        elif risk_level == "HIGH":
            selected_channel = "high"

        else:

            return {
                "triggered": False,
                "reason": (
                    "Automatic alerts are only "
                    "enabled for HIGH or CRITICAL risk."
                )
            }

    else:
        selected_channel = channel

    # --------------------------------------------------------
    # ALERTS DISABLED
    # --------------------------------------------------------

    if not ALERTS_ENABLED:

        record = record_alert(
            "demo_alert",
            risk_result,
            [
                {
                    "success": False,
                    "mode": "demo",
                    "message": (
                        "Alerts are disabled. "
                        "No SMS or call was sent."
                    )
                }
            ]
        )

        return {
            "triggered": True,
            "mode": "demo",
            "record": record
        }

    # --------------------------------------------------------
    # CONTACT CHECK
    # --------------------------------------------------------

    if not EMERGENCY_CONTACT:

        return {
            "triggered": False,
            "reason": (
                "EMERGENCY_CONTACT is not configured."
            )
        }

    message = format_alert_message(
        data,
        risk_result
    )

    results = []

    # ========================================================
    # SMS
    # ========================================================

    if selected_channel in [
        "sms",
        "high",
        "critical"
    ]:

        if cooldown_available("sms"):

            result = send_sms(
                EMERGENCY_CONTACT,
                message
            )

            results.append(result)

            if result.get("success"):
                mark_alert_sent("sms")

        else:

            results.append({
                "success": False,
                "mode": "cooldown",
                "channel": "sms",
                "message": (
                    "SMS skipped because cooldown "
                    "is still active."
                )
            })

    # ========================================================
    # SECONDARY SMS
    # ========================================================

    if (
        EMERGENCY_CONTACT_2
        and selected_channel in [
            "high",
            "critical"
        ]
    ):

        if cooldown_available("sms"):

            result2 = send_sms(
                EMERGENCY_CONTACT_2,
                message
            )

            results.append(result2)

    # ========================================================
    # VOICE CALL
    # ========================================================

    if selected_channel in [
        "call",
        "critical"
    ]:

        if cooldown_available("call"):

            result = make_call(
                EMERGENCY_CONTACT,
                risk_result
            )

            results.append(result)

            if result.get("success"):
                mark_alert_sent("call")

        else:

            results.append({
                "success": False,
                "mode": "cooldown",
                "channel": "call",
                "message": (
                    "Call skipped because cooldown "
                    "is still active."
                )
            })

    # --------------------------------------------------------
    # RECORD
    # --------------------------------------------------------

    record = record_alert(
        f"{selected_channel}_alert",
        risk_result,
        results
    )

    return {
        "triggered": True,
        "mode": (
            "twilio"
            if twilio_is_ready()
            else "not_configured"
        ),
        "record": record
    }


# ============================================================
# AUTOMATIC ALERT EVALUATION
# ============================================================

def evaluate_and_maybe_alert(
    data: Dict[str, Any]
) -> Dict[str, Any]:

    risk_result = calculate_risk(
        data,
        BASELINE,
        []
    )

    return dispatch_alert(
        data,
        risk_result,
        "auto"
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "service": "VITALGUARD AI",
        "status": "ready",
        "version": "2.0.0",
        "message": (
            "VITALGUARD AI backend is working"
        )
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "vitalguard-ai",
        "backend": "FastAPI",
        "risk_engine": "active"
    }


# ============================================================
# BASELINE
# ============================================================

@app.get("/baseline")
def get_baseline():

    return {
        "baseline": BASELINE
    }


@app.post("/baseline")
def baseline():

    return BASELINE


# ============================================================
# SENSOR INPUT
# ============================================================

@app.post("/api/sensor")
def receive_sensor_data(
    data: VitalInput
):

    global LATEST_SENSOR_DATA

    LATEST_SENSOR_DATA = data.model_dump()

    # --------------------------------------------------------
    # Calculate risk
    # --------------------------------------------------------

    risk_result = calculate_risk(
        LATEST_SENSOR_DATA,
        BASELINE,
        []
    )

    # --------------------------------------------------------
    # Automatic emergency alert evaluation
    # --------------------------------------------------------

    alert_result = evaluate_and_maybe_alert(
        LATEST_SENSOR_DATA
    )

    return {
        "success": True,

        "message": (
            "Sensor data received successfully"
        ),

        "data": LATEST_SENSOR_DATA,

        "risk": risk_result,

        "alert": alert_result
    }


# ============================================================
# LIVE DATA
# ============================================================

@app.get("/api/live")
def api_live():

    current = LATEST_SENSOR_DATA.copy()

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

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
            "risk_score",
            risk_result.get("score", 0)
        )

        forecast_result = [
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

    # --------------------------------------------------------
    # Environment
    # --------------------------------------------------------

    temperature = current[
        "ambient_temperature"
    ]

    humidity = current[
        "humidity"
    ]

    heat_index = round(
        temperature
        + 0.05 * max(
            humidity - 40,
            0
        ),
        1
    )

    # --------------------------------------------------------
    # Determine data source
    # --------------------------------------------------------

    is_demo = (
        current.get("timestamp")
        == LIVE_DATA.get("timestamp")
        and current.get("heart_rate")
        == LIVE_DATA.get("heart_rate")
        and current.get("ambient_temperature")
        == LIVE_DATA.get("ambient_temperature")
        and current.get("humidity")
        == LIVE_DATA.get("humidity")
    )

    if is_demo:

        data_source = "SIMULATED_DEMO"

        esp32_connected = False

    else:

        data_source = "EXTERNAL_SENSOR"

        esp32_connected = True

    # --------------------------------------------------------
    # rPPG
    # --------------------------------------------------------

    rppg_available = (
        current.get(
            "rppg_quality",
            0
        ) > 0
    )

    # --------------------------------------------------------
    # Hardware
    # --------------------------------------------------------

    hardware = {
        "esp32_connected": esp32_connected,

        "rppg_connected": rppg_available,

        "fusion_available": True
    }

    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    risk_score = risk_result.get(
        "risk_score",
        risk_result.get("score", 0)
    )

    risk_level = risk_result.get(
        "risk_level",
        "LOW"
    )

    confidence = risk_result.get(
        "confidence",
        0
    )

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    recommendations = risk_result.get(
        "recommended_actions",
        [
            "Reduce physical activity",
            "Move to a cooler environment",
            "Drink water",
            "Recheck vitals"
        ]
    )

    # --------------------------------------------------------
    # Unified response for UI
    # --------------------------------------------------------

    return {

        "available": True,

        "timestamp": current[
            "timestamp"
        ],

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

            "heart_rate": current[
                "heart_rate"
            ],

            "quality": current[
                "rppg_quality"
            ],

            "available": rppg_available
        },

        "vitals": {

            "heart_rate": current[
                "heart_rate"
            ],

            "spo2": current[
                "spo2"
            ],

            "body_temperature": current[
                "body_temperature"
            ],

            "activity_level": current[
                "activity_level"
            ]
        },

        "hardware": hardware,

        "risk": {

            "score": risk_score,

            "level": risk_level,

            "confidence": round(
                confidence * 100,
                1
            ),

            "reasons": risk_result.get(
                "reasons",
                []
            ),

            "explanation": explanation
        },

        "forecast": {

            "points": forecast_result

        },

        "recommendations": recommendations,

        "data_source": data_source
    }


# ============================================================
# COMPATIBILITY LIVE ENDPOINT
# ============================================================

@app.get("/live")
def live():

    return api_live()


# ============================================================
# STATUS
# ============================================================

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


# ============================================================
# RISK ENDPOINT
# ============================================================

@app.post("/risk")
def risk(data: VitalInput):

    d = data.model_dump()

    result = calculate_risk(
        d,
        BASELINE,
        []
    )

    try:

        result["explanation"] = (
            human_explanation(result)
        )

    except Exception:

        result["explanation"] = (
            "Risk calculated using "
            "personalized baseline and "
            "environmental/vital deviations."
        )

    result.pop(
        "feature_snapshot",
        None
    )

    return result


# ============================================================
# CONFIDENCE
# ============================================================

@app.post("/confidence")
def confidence(data: VitalInput):

    d = data.model_dump()

    quality = (
        d.get("rppg_quality", 0)
        +
        d.get("sensor_quality", 0)
    ) / 2

    return {
        "confidence": round(
            quality * 100,
            1
        )
    }


# ============================================================
# FORECAST
# ============================================================

@app.post("/forecast")
def forecast(data: VitalInput):

    d = data.model_dump()

    try:

        result = forecast_risk(
            d,
            BASELINE,
            []
        )

        return {
            "forecast": result
        }

    except Exception:

        risk_result = calculate_risk(
            d,
            BASELINE,
            []
        )

        score = risk_result.get(
            "risk_score",
            risk_result.get("score", 0)
        )

        return {
            "current_risk": score,

            "forecast": [
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
def what_if(
    req: WhatIfRequest
):

    d = req.data.model_dump()

    return simulate(
        d,
        BASELINE,
        [],
        req.changes
    )


# ============================================================
# WHAT-IF COMPATIBILITY
# ============================================================

@app.post("/whatif")
def whatif(
    req: WhatIfRequest
):

    d = req.data.model_dump()

    return simulate(
        d,
        BASELINE,
        [],
        req.changes
    )


# ============================================================
# STANDARD WHAT-IF
# ============================================================

@app.post("/what-if/standard")
def what_if_standard(
    data: VitalInput
):

    return standard_scenarios(
        data.model_dump(),
        BASELINE,
        []
    )


# ============================================================
# ALERT STATUS
# ============================================================

@app.get("/api/alerts/status")
def alerts_status():

    return {

        "alerts_enabled":
            ALERTS_ENABLED,

        "provider":
            (
                "Twilio"
                if twilio_is_ready()
                else "Demo / Not configured"
            ),

        "twilio_sdk_installed":
            TWILIO_AVAILABLE,

        "twilio_configured":
            twilio_is_ready(),

        "emergency_contact_configured":
            bool(EMERGENCY_CONTACT),

        "secondary_contact_configured":
            bool(EMERGENCY_CONTACT_2),

        "trial_mode":
            TWILIO_TRIAL_MODE,

        "automatic_policy": {

            "high":
                "SMS",

            "critical":
                "SMS + voice call",

            "confidence_threshold":
                ALERT_CONFIDENCE_THRESHOLD,

            "cooldown_seconds":
                ALERT_COOLDOWN_SECONDS
        },

        "offline_phone_note": (
            "SMS and calls can reach a mobile phone "
            "without mobile internet on the recipient "
            "device. The cloud backend still requires "
            "network access."
        )
    }


# ============================================================
# ALERT HISTORY
# ============================================================

@app.get("/api/alerts/history")
def alert_history():

    return {
        "count": len(ALERT_HISTORY),
        "alerts": ALERT_HISTORY[-20:]
    }


# ============================================================
# MANUAL EMERGENCY ALERT
# ============================================================

@app.post("/api/alerts/emergency")
def manual_emergency_alert(
    request: AlertRequest
):

    data = request.data.model_dump()

    risk_result = calculate_risk(
        data,
        BASELINE,
        []
    )

    risk_level = str(
        risk_result.get(
            "risk_level",
            "LOW"
        )
    ).upper()

    # --------------------------------------------------------
    # Manual alerts only allowed for HIGH / CRITICAL
    # --------------------------------------------------------

    if risk_level not in [
        "HIGH",
        "CRITICAL"
    ]:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Emergency alert requires "
                    "HIGH or CRITICAL risk."
                ),
                "risk_level": risk_level
            }
        )

    result = dispatch_alert(
        data,
        risk_result,
        request.channel
    )

    return result


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    print("")
    print("=" * 70)
    print(" VITALGUARD AI BACKEND")
    print("=" * 70)

    print(
        " Backend : http://127.0.0.1:8000"
    )

    print(
        " Swagger : http://127.0.0.1:8000/docs"
    )

    print("")

    print(
        " Risk Engine : ACTIVE"
    )

    print(
        " Emergency Alerts : "
        + (
            "ENABLED"
            if ALERTS_ENABLED
            else "DISABLED"
        )
    )

    print(
        " Twilio : "
        + (
            "READY"
            if twilio_is_ready()
            else "NOT CONFIGURED"
        )
    )

    print(
        " Twilio Trial Mode : "
        + str(TWILIO_TRIAL_MODE)
    )

    print("")

    print(" Available endpoints:")

    print(" GET  /")

    print(" GET  /health")

    print(" GET  /api/live")

    print(" POST /api/sensor")

    print(" POST /risk")

    print(" POST /confidence")

    print(" POST /forecast")

    print(" POST /what-if")

    print(" GET  /api/alerts/status")

    print(" GET  /api/alerts/history")

    print(" POST /api/alerts/emergency")

    print("")

    print("=" * 70)
    print("")