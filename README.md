# VITALGUARD — AI/ML + Personal Digital Twin Prototype

This package implements Team Member 4's transparent, deterministic risk engine.

## Pipeline

Sensor/phone data -> validation -> personal baseline -> deviations/trends ->
environment/activity context -> confidence -> risk -> explanation -> forecast -> what-if

## Important prototype limitation

This is a hackathon prototype, not a medical diagnostic system. Risk levels and thresholds
are engineering heuristics. No clinical accuracy is claimed. Synthetic data is used for
demonstration and testing.

## Run

```bash
pip install -r requirements.txt
python demo.py
```

API:

```bash
uvicorn api.main:app --reload
```

Then POST JSON to `/risk`, `/confidence`, `/forecast`, `/what-if`.

## Determinism

Inference is deterministic: identical input + identical baseline produces identical output.
No random operation is used by the inference path.

## Data leakage

If labeled data is later added, split by person or by time. Do not randomly mix observations
from the same person between training and testing.
