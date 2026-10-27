"""Automated unit and integration tests for environmental data ingestion and caching."""
from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from lifelinetwin_geo.weather import (
    HOURLY_VARIABLES,
    STUDY_AREA,
    VARIABLE_UNITS,
    _cache_tag,
    _parse_hourly,
    fetch_forecast,
    get_observations,
    load_observations,
    save_observations,
)


class WeatherDataIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_hourly_structure_and_units(self):
        """Test parsing of raw Open-Meteo JSON into normalized structure."""
        raw_mock = {
            "latitude": 49.415,
            "longitude": 8.6775,
            "elevation": 114.0,
            "timezone": "UTC",
            "hourly": {
                "time": ["2026-10-24T00:00", "2026-10-24T01:00"],
                "temperature_2m": [12.5, 11.8],
                "precipitation": [0.0, 1.2],
                "wind_speed_10m": [15.0, 18.2],
            },
        }
        res = _parse_hourly(raw_mock, source="test_mock")
        self.assertEqual(res["lat"], 49.415)
        self.assertEqual(res["lon"], 8.6775)
        self.assertEqual(res["elevation_m"], 114.0)
        self.assertEqual(res["n_hours"], 2)
        self.assertIn("temperature_2m", res["variables"])
        self.assertEqual(res["variables"]["temperature_2m"]["unit"], "degC")
        self.assertEqual(res["variables"]["temperature_2m"]["n_valid"], 2)
        self.assertEqual(res["variables"]["temperature_2m"]["n_missing"], 0)
        self.assertAlmostEqual(res["variables"]["temperature_2m"]["min"], 11.8)
        self.assertAlmostEqual(res["variables"]["temperature_2m"]["max"], 12.5)

    def test_missing_data_and_nan_handling(self):
        """Verify that None and NaN are appropriately handled without crashes."""
        raw_mock = {
            "latitude": 49.415,
            "longitude": 8.6775,
            "hourly": {
                "time": ["2026-10-24T00:00", "2026-10-24T01:00", "2026-10-24T02:00", "2026-10-24T03:00"],
                "temperature_2m": [10.0, None, float("nan"), 14.0],
            },
        }
        res = _parse_hourly(raw_mock, source="test_mock")
        var_info = res["variables"]["temperature_2m"]
        self.assertEqual(var_info["n_valid"], 2)
        self.assertEqual(var_info["n_missing"], 2)
        self.assertEqual(var_info["min"], 10.0)
        self.assertEqual(var_info["max"], 14.0)
        self.assertEqual(var_info["mean"], 12.0)

    def test_cache_save_and_load(self):
        """Verify that saving and loading observations preserves data completely."""
        test_data = {"test_key": "test_val", "timestamps": ["2026-10-24T00:00"]}
        path = save_observations(test_data, self.temp_dir, "test_tag")
        self.assertTrue(path.exists())

        loaded = load_observations(self.temp_dir, "test_tag")
        self.assertEqual(loaded, test_data)

        # Nonexistent tag returns None
        self.assertIsNone(load_observations(self.temp_dir, "nonexistent"))

    def test_cache_tag_deterministic(self):
        tag1 = _cache_tag(49.415, 8.6775, "forecast", "2026-10-01", "2026-10-08")
        tag2 = _cache_tag(49.415, 8.6775, "forecast", "2026-10-01", "2026-10-08")
        self.assertEqual(tag1, tag2)
        self.assertEqual(len(tag1), 16)

    def test_offline_fallback_on_network_error(self):
        """When network fails, get_observations falls back to cached data."""
        # Create a cached file in temp_dir
        cached_data = {
            "source": "pre_cached_test",
            "timestamps": ["2026-10-24T00:00"],
            "variables": {"temperature_2m": {"values": [15.0]}},
        }
        save_observations(cached_data, self.temp_dir, "sample_cache")

        # Mock requests.get to simulate connection error
        with patch("requests.get", side_effect=requests.ConnectionError("Network down")):
            res = get_observations(cache_dir=self.temp_dir, force_fresh=True)
            self.assertTrue(res.get("cache_hit"))
            self.assertTrue(res.get("offline_fallback"))
            self.assertEqual(res["source"], "pre_cached_test")

    def test_genuine_open_meteo_response(self):
        """Test against genuine cached or live Open-Meteo observations for Heidelberg."""
        # Check if project cache exists; otherwise fetch
        try:
            obs = get_observations(cache_dir="data/heidelberg/weather", past_days=2, forecast_days=1)
            self.assertGreater(obs["n_hours"], 24)
            self.assertIn("temperature_2m", obs["variables"])
            self.assertIn("precipitation", obs["variables"])
            self.assertIn("wind_speed_10m", obs["variables"])
            self.assertEqual(len(obs["timestamps"]), obs["n_hours"])
        except requests.RequestException as e:
            self.skipTest(f"Open-Meteo network request skipped: {e}")


if __name__ == "__main__":
    unittest.main()
