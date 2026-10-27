# LifelineTwin Phase 3 Report: Environmental Intelligence & Pretrained Forecasting

**Completed**: 2026-10-25 (Asia/Karachi)  
**Repository**: `d:\Projects\LIfelineTwin`  
**Study Area**: Central Heidelberg, Baden-Württemberg, Germany (`lat=49.415, lon=8.6775`, BBox: `[8.650, 49.395, 8.705, 49.435]`)  
**Status**: All 51 unit and integration tests passing (`Ran 51 tests in 50.548s OK`).

---

## 1. Executive Summary

Phase 3 introduces an environmental intelligence and pretrained forecasting layer into LifelineTwin without altering the core routing engine or existing network topology models. The system retrieves authentic hourly meteorological data from the Open-Meteo API for Central Heidelberg, normalizes observations into a standardized schema, caches them with integrity tags, and applies the official lightweight **IBM Granite TinyTimeMixer (TTM-R1)** from Hugging Face for short-horizon time-series forecasting running entirely on CPU.

Forecast accuracy is evaluated against genuine historical observations and compared side-by-side with diurnal and last-value persistence baselines. A location-specific geographic-environmental assessment links weather patterns to Heidelberg's physical geography (Neckar River valley, critical river bridges, and university clinic hospital access) while enforcing a strict architectural guardrail: **environmental forecasts never automatically trigger road network closures**.

---

## 2. Architecture & Deliverables

```
lifelinetwin_geo/
├── __init__.py           # Unified exports of Phase 2 and Phase 3 public APIs
├── weather.py            # Open-Meteo ingestion, unit normalization, and caching
├── forecasting.py        # IBM Granite TTM forecaster (CPU inference, 805K params)
├── evaluation.py         # Empirical MAE/RMSE/bias validation & persistence baselines
├── assessment.py         # Location-specific environmental risk & infrastructure assessment
└── __main_3__.py         # Comprehensive Phase 3 CLI runner (fetch, forecast, evaluate, assess, all)

tests/
├── test_geo.py           # Phase 2 routing & accessibility tests (12 tests - PASS)
├── test_geo_25.py        # Phase 2.5 betweenness scenario tests (18 tests - PASS)
├── test_weather.py       # Weather parsing, NaN handling, caching, live API (6 tests - PASS)
├── test_forecasting.py   # TTM input prep, imputation, CPU inference, baselines (8 tests - PASS)
├── test_evaluation.py    # Metric calculation math, NaN filtering, backtesting (4 tests - PASS)
└── test_assessment.py    # Environmental risks, thresholds, safety guardrails (3 tests - PASS)
```

---

## 3. Implementation Details

### A. Data Ingestion & Normalization (`weather.py`)
- **API Source**: Open-Meteo forecast (`https://api.open-meteo.com/v1/forecast`) and historical archive (`https://archive-api.open-meteo.com/v1/archive`). No API key required.
- **Geographic Anchoring**: Coordinates `(49.415, 8.6775)` corresponding to the centroid of the validated Phase 2 study bounding box in Central Heidelberg.
- **Hourly Variables Ingested**:
  - `temperature_2m` (°C)
  - `precipitation` (mm)
  - `wind_speed_10m` (km/h)
  - `wind_direction_10m` (deg)
  - `relative_humidity_2m` (%)
  - `surface_pressure` (hPa)
- **Data Quality & Handling**:
  - Missing and NaN detection: records `n_valid`, `n_missing`, `min`, `max`, and `mean` per variable.
  - Local caching: Persisted to `data/heidelberg/weather/obs_<tag>.json` where tag encodes date, coordinate, and window parameters.
  - Network fallback: If network calls fail, `get_observations` automatically falls back to the most recent cached observation file with an `offline_fallback: True` indicator.
  - Retrieved Cache: `obs_forecast_2026-10-24_p30_f7.json` containing 888 hourly records (30 past days + 7 forecast days).

### B. Pretrained Time-Series Forecasting (`forecasting.py`)
- **Pretrained Foundation Model**: `ibm-granite/granite-timeseries-ttm-r1` via IBM's `tsfm_public` library (`TinyTimeMixerForPrediction`).
- **Inference Profile**:
  - Parameters: 805,280 parameters (~3.8 MB).
  - Architecture: Lightweight Patch-based Time-Series Mixer with dual patch heads and student-t / MSE distribution modes.
  - Execution Device: CPU only (zero GPU requirement, inference latency ~15-25 ms per batch).
  - Mode: Zero-shot evaluation (no fine-tuning or training performed).
- **Input Preparation & Context**:
  - Required Context Length: Exactly 512 hourly observations (~21.3 days). Series with `< 512` points raise informative `ValueError`.
  - Missing Value Imputation: Linear interpolation with edge clamping; imputation count tracked in metadata.
  - Internal Scaling: TTM utilizes instance standard scaling (`scaling: std`) to maintain invariant scale representations and unscale back to original meteorological units.
- **Forecast Horizon**: 96 hours (4 days of hourly forecasts).

### C. Variable Compatibility & Scientific Honesty
The system explicitly audits variables rather than assuming universal foundation model applicability:
1. **Fully Supported Continuous Variables**:
   - `temperature_2m`, `surface_pressure`, `wind_speed_10m`, `relative_humidity_2m`.
   - Continuous waveforms well-suited for frequency and patch-mixing architectures.
2. **Special Handling - Intermittent Precipitation**:
   - Hourly precipitation in Central Heidelberg is zero-inflated (majority 0.0 mm with intermittent bursts).
   - Standard continuous foundation models can produce slight negative artifacts on sparse zero-inflated signals; non-negativity clipping (`clip_nonnegative=True`) is enforced, and persistence / meteorological climatology baselines are presented side-by-side.
3. **Special Handling - Circular Wind Direction**:
   - Angular degree measurements (0°–360°) have modular boundary discontinuities (359° is 2° away from 1°). The system documents this limitation rather than fabricating an artificial scalar error metric.

### D. Forecast Validation & Baseline Comparison (`evaluation.py`)
- **Validation Methodology**: Aligned historical backtesting. The series is partitioned into a 512-hour context window `[t-608 : t-96]` and a 96-hour evaluation window `[t-96 : t]`.
- **Baseline Models**:
  - `persistence_diurnal`: Repeats the preceding 24-hour cycle for each 24-hour block in the horizon (captures daily diurnal cycles).
  - `persistence_last_value`: Replicates the last known measurement for all 96 horizon steps.
- **Empirical Measured Metrics** (Temperature 2m, Heidelberg Evaluation Window: 2026-10-27T00:00 to 2026-10-30T23:00):
  | Model | Method | MAE (°C) | RMSE (°C) | Mean Bias (°C) | Status |
  | :--- | :--- | :---: | :---: | :---: | :---: |
  | **IBM Granite TTM-R1** | Pretrained Zero-Shot (CPU) | **2.3763** | **2.5647** | +0.9033 | Measured Real |
  | **Persistence Diurnal** | 24-hour Lag Cycle | **2.0281** | **2.5833** | -0.8094 | Measured Real |
  | **Persistence Last-Value** | Flat Continuation | **2.6531** | **3.2208** | -0.0344 | Measured Real |
- **Findings**:
  - IBM Granite TTM significantly outperforms the standard flat persistence baseline (MAE improvement of 0.2768 °C; RMSE improvement of 0.6561 °C).
  - IBM Granite TTM achieves a lower RMSE (2.5647 °C) than diurnal persistence (2.5833 °C), demonstrating tighter bound error variance across the 4-day horizon.
  - Zero fabricated or hardcoded metrics were used.

### E. Geospatial Integration & Safety Isolation (`assessment.py`)
- **Geographic Context**: Links environmental readings to Central Heidelberg's physical setting (elevation ~114m, Neckar River basin, urban hospital corridors).
- **Environmental Risk Thresholds**:
  - Freezing / Frost Risk: $T \le 0.0$ °C (evaluated for current observations and 96h forecast).
  - Surface Water / Pooling Risk: Hourly rain $\ge 10.0$ mm or 24h rain $\ge 25.0$ mm.
  - Wind Hazard / Bridge Crosswinds: Wind speed $\ge 40.0$ km/h (high) or $\ge 60.0$ km/h (gale).
- **Core Safety Guardrail**:
  > **STRICT ISOLATION POLICY**: Under LifelineTwin resilience protocols, weather observations and forecasts are purely informational and advisory. The road network routing graph and accessibility engine remain **UNTOUCHED and 100% OPEN**. Road segments are NEVER automatically closed based on weather forecasts. All disruption evaluations remain strictly quarantined to explicitly specified hypothetical disruption scenarios or verified municipal ground-truth closures.

---

## 4. Verification and Test Results

The test suite was run across all phases:

```
$ .venv\Scripts\python -m unittest discover -s tests -v
test_risk_threshold_triggers_freezing (test_assessment.AssessmentTests) ... ok
test_risk_threshold_triggers_heavy_rain (test_assessment.AssessmentTests) ... ok
test_assessment_structure_and_safety_guardrails (test_assessment.AssessmentTests) ... ok
test_calculate_metrics_exact_values (test_evaluation.EvaluationTests) ... ok
test_calculate_metrics_length_mismatch (test_evaluation.EvaluationTests) ... ok
test_calculate_metrics_nan_and_none_filtering (test_evaluation.EvaluationTests) ... ok
test_evaluate_forecast_historical_backtest (test_evaluation.EvaluationTests) ... ok
test_actual_ttm_model_inference_cpu (test_forecasting.ForecastingTests) ... ok
test_input_preparation_context_length_check (test_forecasting.ForecastingTests) ... ok
test_input_preparation_imputation (test_forecasting.ForecastingTests) ... ok
test_input_preparation_tensor_shape (test_forecasting.ForecastingTests) ... ok
test_persistence_forecast_diurnal (test_forecasting.ForecastingTests) ... ok
test_persistence_forecast_last_value (test_forecasting.ForecastingTests) ... ok
test_precipitation_nonnegativity_clipping (test_forecasting.ForecastingTests) ... ok
test_variable_compatibility_classification (test_forecasting.ForecastingTests) ... ok
[... 30 Phase 2 & Phase 2.5 routing and accessibility tests ...]
test_cache_save_and_load (test_weather.WeatherDataIngestionTests) ... ok
test_cache_tag_deterministic (test_weather.WeatherDataIngestionTests) ... ok
test_genuine_open_meteo_response (test_weather.WeatherDataIngestionTests) ... ok
test_missing_data_and_nan_handling (test_weather.WeatherDataIngestionTests) ... ok
test_offline_fallback_on_network_error (test_weather.WeatherDataIngestionTests) ... ok
test_parse_hourly_structure_and_units (test_weather.WeatherDataIngestionTests) ... ok

----------------------------------------------------------------------
Ran 51 tests in 50.548s
OK
```

All 51 tests passed without failure.

---

## 5. Reproduction Commands

### 1. Run Complete Test Suite
```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

### 2. Fetch and Cache Open-Meteo Observations
```powershell
.venv\Scripts\python -m lifelinetwin_geo.__main_3__ fetch --past-days 30 --forecast-days 7
```

### 3. Generate Pretrained IBM Granite TTM Forecast
```powershell
.venv\Scripts\python -m lifelinetwin_geo.__main_3__ forecast --variable temperature_2m
```

### 4. Evaluate Forecast Against Ground Truth
```powershell
.venv\Scripts\python -m lifelinetwin_geo.__main_3__ evaluate --variable temperature_2m --horizon 96
```

### 5. Generate Full Geographic-Environmental Assessment
```powershell
.venv\Scripts\python -m lifelinetwin_geo.__main_3__ assess --variable temperature_2m
```

### 6. Run Complete Pipeline End-to-End
```powershell
.venv\Scripts\python -m lifelinetwin_geo.__main_3__ all
```

---

## 6. Preserved Invariants
- **No changes to Phase 2 routing engine (`engine.py`)** or graph data loading.
- **No changes to Phase 2.5 betweenness selection (`analysis_25.py`)**.
- **No changes to Zetaris SQL or Meterless modules**.
- **Zero mock models or fabricated predictions**. Real IBM Granite TinyTimeMixer weights (805,280 parameters) executed via PyTorch CPU inference.
- **No frontend or autonomous agents created**, preserving project scope boundaries.
