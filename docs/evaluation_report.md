# Evaluation Plan

## Current status

This prototype uses synthetic/demo observations. Therefore it does **not** report medical
accuracy, sensitivity, specificity, or clinical performance.

## Tests

1. Determinism: same input and baseline -> same output.
2. Range: risk remains 0–100; confidence remains 0–1.
3. Heat sensitivity: higher ambient heat/humidity should not silently reduce risk when
   all other values remain equal.
4. Baseline sensitivity: changing a person's baseline changes deviation features.
5. Signal confidence: lower rPPG/sensor quality lowers confidence.
6. Recovery/what-if: simulated rest/cooler environment can be compared with the current state.

## Future ML evaluation

If labeled longitudinal data becomes available:
- split by person where possible;
- otherwise use time-ordered train/validation/test splits;
- keep all preprocessing fitted on training data only;
- compare transparent baseline against logistic regression/random forest/gradient boosting;
- report metrics with confidence intervals where appropriate;
- never claim clinical performance from synthetic data.
