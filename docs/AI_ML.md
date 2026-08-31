# MissionGuard AI — AI/ML Pipeline

This document distinguishes exactly which parts of MissionGuard AI are **deterministic**, which are **statistical/ML**, and which are **LLM-based**, per the actual code.

| Layer                                             | Type                                             | Where                             |
| ------------------------------------------------- | ------------------------------------------------ | --------------------------------- |
| Telemetry generation                              | Deterministic (seeded RNG)                       | `app/services/simulator.py`       |
| Feature engineering                               | Deterministic (pandas rolling stats)             | `app/ml/features.py`              |
| Anomaly detection                                 | Machine learning                                 | `app/ml/anomaly.py`               |
| Forecasting                                       | Statistical (linear regression)                  | `app/ml/forecasting.py`           |
| Risk scoring                                      | Deterministic (weighted formula)                 | `app/services/risk.py`            |
| Mission feasibility                               | Deterministic (rule-based constraint checks)     | `app/services/mission_planner.py` |
| Conjunction screening                             | Deterministic (seeded simplified geometry)       | `app/services/ssa.py`             |
| Explanation / recommendations / Copilot / reports | LLM (Granite or deterministic template fallback) | `app/services/explain.py`         |

## 1. Telemetry Simulation

`generate_scenario()` produces `TelemetryPoint` records for one of six scenarios (`normal`, `battery_degradation`, `thermal_anomaly`, `communication_anomaly`, `sensor_anomaly`, `compound_anomaly`), using `numpy.random.default_rng(seed)` so a given `(scenario, severity, seed)` combination is fully reproducible. Each scenario perturbs specific parameters over the run's duration (e.g. `battery_degradation` linearly drops `battery_voltage` and raises `power_consumption` and `battery_current` proportional to `severity`). Thirteen raw parameters are generated per point (`battery_voltage`, `battery_current`, `power_consumption`, `temperature`, `solar_output`, `signal_strength`, `fuel_level`, `gyro_x/y/z`, `cpu_usage`, `memory_usage`, `radiation_level`).

## 2. Feature Engineering

`app/ml/features.py` defines two feature sets:

- **`build_features()`** — the full feature set (rolling mean/std, percent change, rate of change, and two cross-parameter ratios) used for the Telemetry Explorer's display calculations.
- **`model_feature_matrix()`** — a deliberately compact feature set (raw value + rate of change + rolling mean) for only six parameters (`battery_voltage`, `battery_current`, `power_consumption`, `temperature`, `signal_strength`, `cpu_usage`), used specifically to fit/score the anomaly detectors. A full 60+ column matrix was tried first during development and diluted the real signal in noise dimensions given a short baseline window; the compact set is what the detectors actually use.

## 3. Anomaly Detection

`app/ml/anomaly.py` defines an abstract `AnomalyDetector` interface (`fit(X_baseline)`, `decision_scores(X)` where higher = more normal) with three implementations, selectable via the `detector` query parameter on `POST /api/telemetry/simulate`:

- **`IsolationForestDetector`** (default) — `sklearn.ensemble.IsolationForest(n_estimators=200, contamination="auto", random_state=42)`.
- **`OneClassSVMDetector`** — `sklearn.svm.OneClassSVM(kernel="rbf", nu=0.15, gamma="scale")` with `StandardScaler`.
- **`AutoencoderDetector`** — `sklearn.neural_network.MLPRegressor(hidden_layer_sizes=(8,3,8), activation="tanh")` trained as an input=output autoencoder; the negative mean-squared reconstruction error is used as the "more normal = higher" score, matching the other two detectors' convention.

Each detector is fit on the first 35% of a telemetry run (treated as the "baseline"), then scores every point in the run. `raw_to_scores()` normalizes each detector's raw decision-function output against the _baseline window's own_ min/max spread, then maps it to a 0-100 scale.

### Score bands (prototype thresholds, not certification standards)

```
0-30    NORMAL
31-60   LOW
61-80   WARNING
81-100  CRITICAL
```

`score_band()` is the single function used everywhere this mapping happens.

### Explainability

`_top_contributors()` ranks each of eleven telemetry parameters (excluding `fuel_level` and `solar_output`, which have expected non-anomalous baseline dynamics of their own) by z-score deviation from the baseline window, and returns the top 4 as `AnomalyContributor` objects with normalized relative contribution — this is what powers the contributor bars in the Anomaly Center UI. This is a lightweight, interpretable stand-in for SHAP-style attribution, not SHAP itself.

### Confidence

`confidence` on each `PointResult`/`Anomaly` is derived from baseline sample size (`0.5 + 0.5 * min(baseline_n, 30) / 30`, clipped to `[0.5, 0.95]`) — it reflects how much baseline data the model had to work with, not a calibrated probability of correctness. The anomaly score itself is explicitly documented and labeled (see `config.py`) as a prototype metric, never presented as a failure probability.

### Incident deduplication (hysteresis)

`analyze_run()` in `app/services/pipeline.py` does not create one `Anomaly` record per abnormal point. It uses a cooldown window (`max(3, len(results)//15)` points) so a signal oscillating in and out of the `WARNING` band is treated as one ongoing incident rather than many fragmented ones; the recorded anomaly's score/band is updated to the worst point seen during the incident.

## 4. Forecasting

`forecast_parameter()` in `app/ml/forecasting.py` fits an ordinary least-squares linear trend (`numpy.linalg.lstsq`) to a parameter's history. For four parameters with defined prototype warning thresholds (`battery_voltage`, `temperature`, `signal_strength`, `fuel_level`), it also computes an estimated hours-until-threshold-crossing, **only when the trend is actually moving toward the threshold** and there are at least `MIN_POINTS = 6` observations. When data is insufficient, `sufficient_data: false` and a `note` explaining why is returned instead of a fabricated estimate — this is enforced in code, not just documentation.

## 5. Risk Engine

`compute_risk()` in `app/services/risk.py` is a fully deterministic weighted formula:

```
subsystem_risk = 0.6 * anomaly_score + 0.4 * trend_component
weighted       = subsystem_risk * criticality[subsystem]
overall_score  = sum(weighted) / sum(criticality)
```

`trend_component` scales from 0-100 based on how close the forecast's estimated threshold-crossing is to a 24-hour horizon. `SUBSYSTEM_CRITICALITY` weights (`power: 1.0`, `navigation: 0.9`, `propulsion: 0.85`, `thermal: 0.8`, `communication: 0.7`, `onboard_compute: 0.6`) are fixed constants in `config.py`. No LLM call is involved anywhere in this calculation.

## 6. Mission Feasibility (Mission Planner)

`evaluate_mission_plan()` in `app/services/mission_planner.py` checks five constraints against current telemetry and forecasted values:

- **Power**: projects power consumption forward using the forecast module, compares against a fixed prototype 250W bus budget minus the proposed activity's required power.
- **Thermal**: projects temperature forward, compares against the request's `max_temperature_c`.
- **Fuel**: compares current `fuel_level` against the request's `min_fuel_pct`.
- **Communication**: compares current `signal_strength` against fixed thresholds, only if `requires_communication` is set.
- **Attitude**: compares current gyro-vector magnitude against fixed thresholds, only if `requires_attitude_maneuver` is set.

Each constraint returns `SAFE`/`MODERATE`/`UNSAFE`/`UNKNOWN`; the overall verdict is `UNSAFE` if any constraint is `UNSAFE`, `CONDITIONAL` if any is `MODERATE`/`UNKNOWN`, else `SAFE`. This logic is pure Python arithmetic — the AI provider only narrates the already-computed result via `explain_mission_plan()`.

## 7. ML Evaluation

`app/ml/evaluation.py` provides two real (not fabricated) evaluation functions:

- **`evaluate_detectors()`**: generates a _fresh, separately-seeded_ run of a named scenario, labels ground truth from the simulator's own known injection onset point (45% into the run by default), fits and scores all three detectors against it, and computes precision, recall, F1, false-positive-rate, and detection latency (points between true onset and first correct flag) from the actual predictions.
- **`evaluate_forecast()`**: generates a fresh run, fits the linear forecast on the first 80% of points, and computes MAE/RMSE of the projection against the actual held-out final 20%.

Both are exposed via `GET /api/models/evaluate` and `GET /api/models/evaluate-forecast`. The evaluation dataset is always simulated, and the code/docs say so explicitly — ground truth comes from the simulator's known injection point, not hand-labeled real telemetry, so these numbers measure _relative_ detector behavior on simulated data, not certified real-world accuracy.

## 8. LLM Layer

See `GRANITE_INTEGRATION.md` for full detail. In summary: the LLM layer (`GraniteProvider` interface) receives only the structured `EvidencePackage`/`MissionPlanEvaluation`/`ConjunctionEvent` objects described above — never raw telemetry — and is responsible only for natural-language explanation, recommendation phrasing, Copilot answers, and report narration. It cannot alter any anomaly score, risk score, or feasibility verdict.

## 9. Limitations

- Anomaly thresholds and the risk formula's weights are prototype constants tuned for demo scenarios, not derived from real spacecraft engineering data.
- The autoencoder is a small `MLPRegressor`, not a deep learning framework model (no PyTorch/TensorFlow in this build).
- Forecasting is a single linear trend fit per call — no ARIMA/LSTM, no confidence intervals around the projected line.
- Evaluation metrics are computed on simulated data with simulator-known ground truth; they are not validated against any real mission dataset.
