"""Explicit, repository-relative defaults; no dependency on process cwd."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(default_factory=lambda: Path(os.getenv(
        "LIFELINETWIN_DATABASE", str(ROOT / "data/backend/lifelinetwin.sqlite3"))))
    geographic_cache: Path = ROOT / "data/heidelberg"
    weather_snapshot: Path = field(default_factory=lambda: Path(os.getenv(
        "LIFELINETWIN_WEATHER_SNAPSHOT", str(ROOT / "data/heidelberg/weather/obs_forecast_2026-10-24_p30_f7.json"))))
    model_cache: Path = ROOT / ".runtime/huggingface/hub"
