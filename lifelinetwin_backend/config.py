"""Explicit, repository-relative defaults; no dependency on process cwd."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from .region import REGION_ID

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(default_factory=lambda: Path(os.getenv(
        "LIFELINETWIN_DATABASE", str(ROOT / "data/backend/lifelinetwin.sqlite3"))))
    geographic_cache: Path = ROOT / f"data/{REGION_ID}"
    weather_snapshot: Path = field(default_factory=lambda: Path(os.getenv(
        "LIFELINETWIN_WEATHER_SNAPSHOT", str(ROOT / ("data/houston/weather/obs_current-context.json" if REGION_ID == 'houston' else "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json")))))
    model_cache: Path = ROOT / ".runtime/huggingface/hub"
