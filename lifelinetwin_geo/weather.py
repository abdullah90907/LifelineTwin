"""Open-Meteo environmental data ingestion and local caching for LifelineTwin.

Provides structured hourly observations for the Heidelberg study area.
No API key required. All HTTP is isolated through fetch_* functions so
tests can patch at the requests level.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Study-area constants (matches Phase 2 bbox centre)
# ---------------------------------------------------------------------------
STUDY_AREA: dict[str, Any] = {
    "name": "Central Heidelberg, Baden-Wuerttemberg, Germany",
    "lat": 49.415,
    "lon": 8.6775,
    "bbox_wsen": (8.650, 49.395, 8.705, 49.435),
    "timezone": "Europe/Berlin",
}

HOURLY_VARIABLES: list[str] = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "relative_humidity_2m",
    "surface_pressure",
]

VARIABLE_UNITS: dict[str, str] = {
    "temperature_2m":       "degC",
    "precipitation":        "mm",
    "wind_speed_10m":       "km/h",
    "wind_direction_10m":   "deg",
    "relative_humidity_2m": "pct",
    "surface_pressure":     "hPa",
}

_FORECAST_BASE  = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE_BASE   = "https://archive-api.open-meteo.com/v1/archive"
_TIMEOUT        = 30


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_hourly(raw: dict, source: str) -> dict:
    """Convert raw Open-Meteo hourly JSON to a normalised observation dict."""
    hourly = raw.get("hourly", {})
    times  = hourly.get("time", [])
    result: dict[str, Any] = {
        "source":            source,
        "retrieved_utc":     datetime.now(timezone.utc).isoformat(),
        "lat":               raw.get("latitude", STUDY_AREA["lat"]),
        "lon":               raw.get("longitude", STUDY_AREA["lon"]),
        "elevation_m":       raw.get("elevation"),
        "timezone":          raw.get("timezone", STUDY_AREA["timezone"]),
        "hourly_units":      raw.get("hourly_units", {}),
        "timestamps":        times,
        "n_hours":           len(times),
        "variables":         {},
    }
    for var in HOURLY_VARIABLES:
        values = hourly.get(var)
        if values is None:
            continue
        valid   = [v for v in values if v is not None and not _is_nan(v)]
        missing = sum(1 for v in values if v is None or _is_nan(v))
        result["variables"][var] = {
            "values":         values,
            "unit":           VARIABLE_UNITS.get(var, ""),
            "n_valid":        len(valid),
            "n_missing":      missing,
            "min":            min(valid) if valid else None,
            "max":            max(valid) if valid else None,
            "mean":           sum(valid) / len(valid) if valid else None,
        }
    return result


def _is_nan(v: Any) -> bool:
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return False


def _cache_tag(lat: float, lon: float, kind: str, start: str, end: str) -> str:
    key = f"{lat:.4f}_{lon:.4f}_{kind}_{start}_{end}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------

def fetch_forecast(
    lat: float = STUDY_AREA["lat"],
    lon: float = STUDY_AREA["lon"],
    past_days: int = 30,
    forecast_days: int = 7,
    variables: list[str] | None = None,
    timeout: int = _TIMEOUT,
) -> dict:
    """Fetch hourly forecast + recent-past data from Open-Meteo forecast API.

    Returns a normalised observation dict. past_days controls how many days
    of recent history are included alongside the forecast window.
    """
    variables = variables or HOURLY_VARIABLES
    params = {
        "latitude":       lat,
        "longitude":      lon,
        "hourly":         ",".join(variables),
        "past_days":      past_days,
        "forecast_days":  forecast_days,
        "timezone":       "UTC",
        "timeformat":     "iso8601",
    }
    resp = requests.get(_FORECAST_BASE, params=params, timeout=timeout)
    resp.raise_for_status()
    return _parse_hourly(resp.json(), source=_FORECAST_BASE)


def fetch_historical(
    lat: float = STUDY_AREA["lat"],
    lon: float = STUDY_AREA["lon"],
    start_date: str | None = None,
    end_date: str | None = None,
    variables: list[str] | None = None,
    timeout: int = _TIMEOUT,
) -> dict:
    """Fetch historical hourly data from Open-Meteo archive API.

    Dates are ISO-8601 strings: 'YYYY-MM-DD'. Defaults to the last 60 days.
    """
    variables  = variables or HOURLY_VARIABLES
    today      = datetime.now(timezone.utc).date()
    end_date   = end_date   or (today - timedelta(days=1)).isoformat()
    start_date = start_date or (today - timedelta(days=60)).isoformat()
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start_date,
        "end_date":   end_date,
        "hourly":     ",".join(variables),
        "timezone":   "UTC",
        "timeformat": "iso8601",
    }
    resp = requests.get(_ARCHIVE_BASE, params=params, timeout=timeout)
    resp.raise_for_status()
    return _parse_hourly(resp.json(), source=_ARCHIVE_BASE)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def save_observations(data: dict, cache_dir: str | Path, tag: str) -> Path:
    """Persist observations to <cache_dir>/obs_<tag>.json. Returns path."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"obs_{tag}.json"
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return path


def load_observations(cache_dir: str | Path, tag: str) -> dict | None:
    """Load cached observations; return None if not found."""
    path = Path(cache_dir) / f"obs_{tag}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_observations(
    cache_dir: str | Path = "data/heidelberg/weather",
    past_days: int = 30,
    forecast_days: int = 7,
    force_fresh: bool = False,
    lat: float = STUDY_AREA["lat"],
    lon: float = STUDY_AREA["lon"],
) -> dict:
    """Return observations from cache if available, otherwise fetch and cache.

    The cache tag encodes the request parameters so different windows are
    stored separately. force_fresh=True always re-fetches.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    tag   = f"forecast_{today}_p{past_days}_f{forecast_days}"
    if not force_fresh:
        cached = load_observations(cache_dir, tag)
        if cached is not None:
            cached["cache_hit"] = True
            return cached
    try:
        data = fetch_forecast(lat=lat, lon=lon, past_days=past_days,
                              forecast_days=forecast_days)
        data["cache_tag"] = tag
        data["cache_hit"] = False
        save_observations(data, cache_dir, tag)
        return data
    except requests.RequestException as exc:
        # If network fails, search cache_dir for any existing cached observation file
        cd = Path(cache_dir)
        cached_files = sorted(cd.glob("obs_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if cached_files:
            fallback = json.loads(cached_files[0].read_text(encoding="utf-8"))
            fallback["cache_hit"] = True
            fallback["offline_fallback"] = True
            fallback["fallback_warning"] = f"Network fetch failed ({exc}); loaded cached data from {cached_files[0].name}"
            return fallback
        raise

