"""Geographic-environmental assessment module for LifelineTwin.

Synthesizes authentic environmental observations and AI forecasts with
Heidelberg's geographic study area. Evaluates meteorological risk indicators
(freezing, surface runoff, severe wind gusts) while strictly isolating the
routing engine and maintaining guardrails against automated road closures.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from .weather import STUDY_AREA


# ---------------------------------------------------------------------------
# Meteorological threshold definitions
# ---------------------------------------------------------------------------
RISK_THRESHOLDS = {
    "freezing_temperature_c": 0.0,
    "heavy_rain_hourly_mm": 10.0,
    "heavy_rain_24h_mm": 25.0,
    "gale_wind_speed_kmh": 60.0,
    "high_wind_speed_kmh": 40.0,
}


def assess_environmental_risks(
    current_temp: float | None,
    forecast_temp_min: float | None,
    forecast_precip_max_1h: float | None,
    forecast_precip_total: float | None,
    forecast_wind_max: float | None,
) -> list[dict[str, Any]]:
    """Evaluate specific environmental risk indicators against defined thresholds."""
    indicators = []

    # 1. Freezing / Black Ice Risk
    freezing_active = (current_temp is not None and current_temp <= RISK_THRESHOLDS["freezing_temperature_c"])
    freezing_forecast = (forecast_temp_min is not None and forecast_temp_min <= RISK_THRESHOLDS["freezing_temperature_c"])
    freezing_severity = "high" if freezing_active else ("medium" if freezing_forecast else "low")
    indicators.append({
        "risk": "freezing_road_conditions",
        "severity": freezing_severity,
        "active_now": freezing_active,
        "forecast_event": freezing_forecast,
        "threshold": f"<= {RISK_THRESHOLDS['freezing_temperature_c']} degC",
        "details": (
            f"Current temperature {current_temp} degC, minimum forecast {forecast_temp_min} degC. "
            + ("Sub-zero temperatures detected or anticipated; potential bridge frost."
               if (freezing_active or freezing_forecast) else "Temperatures remain above freezing.")
        ),
    })

    # 2. Surface Water / Runoff Risk
    heavy_rain = (forecast_precip_max_1h is not None and forecast_precip_max_1h >= RISK_THRESHOLDS["heavy_rain_hourly_mm"])
    sustained_rain = (forecast_precip_total is not None and forecast_precip_total >= RISK_THRESHOLDS["heavy_rain_24h_mm"])
    rain_severity = "high" if (heavy_rain or sustained_rain) else ("medium" if (forecast_precip_total or 0) > 5.0 else "low")
    indicators.append({
        "risk": "surface_water_pooling_runoff",
        "severity": rain_severity,
        "active_now": False,
        "forecast_event": (heavy_rain or sustained_rain),
        "threshold": f">= {RISK_THRESHOLDS['heavy_rain_hourly_mm']} mm/h or >= {RISK_THRESHOLDS['heavy_rain_24h_mm']} mm/event",
        "details": (
            f"Max 1h precipitation {forecast_precip_max_1h} mm, total horizon precipitation {forecast_precip_total} mm. "
            + ("Intense precipitation forecasted; low-lying Neckar embankment roads may experience pooling."
               if (heavy_rain or sustained_rain) else "Precipitation within normal urban drainage capacities.")
        ),
    })

    # 3. Wind / Debris Hazard
    gale_wind = (forecast_wind_max is not None and forecast_wind_max >= RISK_THRESHOLDS["gale_wind_speed_kmh"])
    high_wind = (forecast_wind_max is not None and forecast_wind_max >= RISK_THRESHOLDS["high_wind_speed_kmh"])
    wind_severity = "high" if gale_wind else ("medium" if high_wind else "low")
    indicators.append({
        "risk": "high_wind_bridge_crosswinds",
        "severity": wind_severity,
        "active_now": False,
        "forecast_event": high_wind,
        "threshold": f">= {RISK_THRESHOLDS['high_wind_speed_kmh']} km/h",
        "details": (
            f"Peak forecast wind speed {forecast_wind_max} km/h. "
            + ("Strong crosswinds on Neckar bridges and potential tree-fall risk."
               if high_wind else "Wind speeds remain within safe driving tolerances.")
        ),
    })

    return indicators


def generate_environmental_assessment(
    observations: dict[str, Any],
    forecast: dict[str, Any] | None = None,
    study_area: dict[str, Any] = STUDY_AREA,
) -> dict[str, Any]:
    """Produce a structured geographic-environmental assessment for LifelineTwin.

    Integrates authentic observations with AI/persistence forecasts for the
    Heidelberg study area. Adheres strictly to the safety rule: NO AUTOMATIC
    ROAD CLOSURES ARE INFERRED FROM WEATHER DATA.
    """
    retrieved_utc = observations.get("retrieved_utc", datetime.now(timezone.utc).isoformat())
    obs_vars = observations.get("variables", {})

    # Extract recent 24-hour observation statistics
    temps = obs_vars.get("temperature_2m", {}).get("values", [])
    valid_temps = [t for t in temps if t is not None and not (isinstance(t, float) and math.isnan(t))]
    current_temp = valid_temps[-1] if valid_temps else None
    recent_24h_temps = valid_temps[-24:] if len(valid_temps) >= 24 else valid_temps

    precips = obs_vars.get("precipitation", {}).get("values", [])
    valid_precips = [p for p in precips if p is not None and not (isinstance(p, float) and math.isnan(p))]
    recent_24h_precip = sum(valid_precips[-24:]) if len(valid_precips) >= 24 else (sum(valid_precips) if valid_precips else 0.0)

    winds = obs_vars.get("wind_speed_10m", {}).get("values", [])
    valid_winds = [w for w in winds if w is not None and not (isinstance(w, float) and math.isnan(w))]
    current_wind = valid_winds[-1] if valid_winds else None
    recent_24h_max_wind = max(valid_winds[-24:]) if len(valid_winds) >= 24 else (max(valid_winds) if valid_winds else None)

    obs_summary = {
        "current_temperature_degC": current_temp,
        "recent_24h_temp_min_degC": min(recent_24h_temps) if recent_24h_temps else None,
        "recent_24h_temp_max_degC": max(recent_24h_temps) if recent_24h_temps else None,
        "recent_24h_precipitation_sum_mm": round(recent_24h_precip, 2),
        "current_wind_speed_kmh": current_wind,
        "recent_24h_max_wind_kmh": recent_24h_max_wind,
        "total_observed_hours": observations.get("n_hours", len(temps)),
    }

    # Extract forecast highlights if available
    forecast_summary: dict[str, Any] = {}
    f_temp_min = None
    f_precip_max = None
    f_precip_total = None
    f_wind_max = None

    if forecast is not None:
        f_vals = forecast.get("forecast_values", [])
        f_var = forecast.get("variable", "unknown")
        f_horizon = forecast.get("forecast_horizon_hours", len(f_vals))
        f_model = forecast.get("model_id", "unspecified")

        forecast_summary = {
            "model_id": f_model,
            "forecast_variable": f_var,
            "horizon_hours": f_horizon,
            "forecast_start": forecast.get("forecast_timestamps", [None])[0],
            "forecast_end": forecast.get("forecast_timestamps", [None])[-1],
            "summary_min": round(min(f_vals), 3) if f_vals else None,
            "summary_max": round(max(f_vals), 3) if f_vals else None,
            "summary_mean": round(sum(f_vals) / len(f_vals), 3) if f_vals else None,
        }

        if f_var == "temperature_2m" and f_vals:
            f_temp_min = min(f_vals)
        elif f_var == "precipitation" and f_vals:
            f_precip_max = max(f_vals)
            f_precip_total = sum(f_vals)
        elif f_var == "wind_speed_10m" and f_vals:
            f_wind_max = max(f_vals)

    # Compute risk indicators
    risk_indicators = assess_environmental_risks(
        current_temp=current_temp,
        forecast_temp_min=f_temp_min,
        forecast_precip_max_1h=f_precip_max,
        forecast_precip_total=f_precip_total,
        forecast_wind_max=f_wind_max,
    )

    return {
        "assessment_type": "GeographicEnvironmentalAssessment",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "study_area": {
            "name": study_area["name"],
            "lat": study_area["lat"],
            "lon": study_area["lon"],
            "bbox_wsen": study_area["bbox_wsen"],
            "timezone": study_area["timezone"],
        },
        "observation_summary": obs_summary,
        "forecast_summary": forecast_summary,
        "environmental_risk_indicators": risk_indicators,
        "geospatial_infrastructure_context": {
            "topography": "Upper Rhine Rift valley along the Neckar River (elevation ~114m)",
            "key_critical_structures": [
                "Theodor-Heuss-Brücke (central arterial river crossing)",
                "Ernst-Walz-Brücke (hospital campus transit crossing)",
                "Universitätsklinikum Heidelberg (Im Neuenheimer Feld hospital cluster)",
            ],
            "policy_isolation_statement": (
                "STRICT ISOLATION PROTOCOL: Environmental observations and AI forecasts are informational "
                "context only. The LifelineTwin routing graph and accessibility engine remain UNMODIFIED. "
                "Road segments are NEVER automatically closed based on weather predictions. Closures must "
                "remain explicit hypothetical disruption scenarios evaluated under controlled human oversight."
            ),
            "routing_engine_unaffected": True,
        },
        "evidence": [
            f"Open-Meteo observation source: {observations.get('source')}",
            f"Observation retrieval UTC: {retrieved_utc}",
            f"Observation cache status: hit={observations.get('cache_hit', False)}",
            f"Pretrained forecaster: {forecast.get('model_id') if forecast else 'Not attached'}",
        ],
    }
