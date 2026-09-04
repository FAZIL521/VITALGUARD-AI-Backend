# VITALGUARD Feature Specification

| Feature | Meaning | Role |
|---|---|---|
| hr_deviation_z | HR distance from personal baseline | abnormality |
| spo2_deviation_z | SpO₂ distance from baseline | abnormality |
| temperature_deviation_z | temperature distance from baseline | abnormality |
| hr_slope | recent HR direction | temporal |
| spo2_slope | recent SpO₂ direction | temporal |
| temperature_slope | recent temperature direction | temporal |
| ambient_temperature | environmental heat context | environment |
| humidity | environmental moisture context | environment |
| activity_level | rest/light/moderate/high context | adjustment |
| rppg_quality | phone camera signal quality | confidence |
| sensor_quality | sensor pipeline quality | confidence |

Risk score is a transparent weighted heuristic, not a clinical probability.
