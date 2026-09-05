# VITALGUARD — AI Risk + Emergency Alert Backend

This is the Team Member 4 prototype backend for VITALGUARD. It keeps the deterministic personal-baseline risk engine and adds an emergency alert layer.

## New emergency capabilities

- `POST /api/sensor` accepts a sensor packet, evaluates risk, and automatically evaluates the alert policy.
- `POST /api/alerts/emergency` manually sends an SMS/call for a HIGH or CRITICAL current risk.
- `GET /api/alerts/history` returns recent in-memory alert history.
- `GET /api/alerts/status` returns the alert configuration/policy.
- `GET /api/health` reports backend and alert-provider readiness.
- HIGH risk -> SMS.
- CRITICAL risk -> SMS + automated voice call.
- Confidence threshold and cooldown reduce accidental repeated alerts.
- Without Twilio credentials, the backend remains safe in demo/not-configured mode and records attempted alert actions instead of sending real messages/calls.

## Important safety/prototype note

This is a hackathon prototype, not a medical diagnostic system. Risk thresholds are engineering heuristics. The alert layer should be demonstrated as a safety-notification mechanism, not as a diagnosis or guaranteed emergency response.

## Twilio setup

The implementation uses the Twilio Python SDK for SMS and voice calls. Twilio's official Python examples use `Client(account_sid, auth_token)`, `client.messages.create(...)` for SMS, and `client.calls.create(...)` for outbound calls.

Set these environment variables in your local shell or deployment platform:

```text
ALERTS_ENABLED=true
EMERGENCY_CONTACT=+91XXXXXXXXXX
EMERGENCY_CONTACT_2=
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
ALERT_CONFIDENCE_THRESHOLD=0.75
ALERT_COOLDOWN_SECONDS=600
```

Use E.164 phone-number formatting (`+` plus country code).

**Do not put credentials in source code or commit `.env`.**

## Run locally

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Open Swagger at:

```text
http://127.0.0.1:8000/docs
```

## Test without real SMS/calls

Leave:

```text
ALERTS_ENABLED=false
```

The API will calculate risk and show whether an alert would be triggered, without contacting anyone.

## Render deployment

Add the same environment variables under the Render service's Environment settings. Keep the start command:

```text
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Do not put Twilio credentials in GitHub.

## Offline-phone behavior

A recipient phone does not need internet/mobile data to receive a normal SMS or voice call; cellular service is sufficient. However, a cloud backend still needs its own network connection to contact the SMS/voice provider.

For a true emergency path when the patient's device has no internet, add a GSM/LTE module to the ESP32. That module can send the emergency SMS/call directly over the cellular network, independently of the cloud backend.

## Existing endpoints

- `POST /baseline`
- `POST /risk`
- `POST /confidence`
- `POST /forecast`
- `POST /what-if`
- `POST /what-if/standard`
- `GET /api/live`

## Data storage

Sensor data and alert history are currently in RAM for prototype simplicity. A production system should use persistent storage, authentication, rate limiting, audit logging, secret management, and stronger alert validation.
