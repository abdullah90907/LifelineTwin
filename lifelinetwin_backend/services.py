"""Deterministic adapters around existing tools; weather never selects closures."""
import hashlib
import json
from datetime import datetime, timezone
from itertools import combinations
from threading import Lock

from .config import Settings
from .schemas import EnvironmentRequest, EnvironmentResult, GeographicRequest, GeographicResult

MODEL_ID = "ibm-granite/granite-timeseries-ttm-r1"
MODEL_REVISION = "f04bebdd4c13475b006ce72672e74c9dc28871dc"


def utc(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class ToolUnavailable(RuntimeError):
    """A required real data/model dependency cannot produce a result."""


class Tools:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_lock = Lock()
        self.forecaster = None

    def geographic(self, request: GeographicRequest) -> GeographicResult:
        from lifelinetwin_geo.data import load
        from lifelinetwin_geo.engine import analyze, accessibility, close_segments
        from lifelinetwin_geo.analysis_25 import choose_closures_by_betweenness

        # Existing loader verifies every manifest checksum; no download path exists here.
        graph, origins, facilities, manifest = load(self.settings.geographic_cache)
        if request.context.origin_ids:
            known = {o["id"] for o in origins}
            if not set(request.context.origin_ids) <= known:
                raise ValueError("Unknown origin ID; use origin IDs from the cached Heidelberg dataset")
            origins = [o for o in origins if o["id"] in request.context.origin_ids]
        closures = [dict(s.model_dump(), hypothetical=True) for s in request.closures]
        if request.selection == "betweenness":
            closures = choose_closures_by_betweenness(
                graph, accessibility(graph, origins, facilities), count=request.count)
        result = analyze(graph, origins, facilities, closures=closures)
        pairs = []
        if len(closures) >= 2 and not any(
            r["reconnected_origins"] or r["distance_saved_m_for_already_reachable"] > 1e-8
            for r in result["restorations"]
        ):
            for pair in combinations(closures, 2):
                ids = sorted(c["id"] for c in pair)
                restored = accessibility(close_segments(graph, [c for c in closures if c["id"] not in ids]), origins, facilities)
                reconnected = sum(a["distance_m"] is None and b["distance_m"] is not None
                                  for a, b in zip(result["disrupted"], restored, strict=True))
                saved = sum(max(0.0, a["distance_m"] - b["distance_m"])
                            for a, b in zip(result["disrupted"], restored, strict=True)
                            if a["distance_m"] is not None and b["distance_m"] is not None)
                pairs.append({"reopened": ids, "reconnected_origins": reconnected,
                              "distance_saved_m_for_already_reachable": saved, "accessibility": restored})
            pairs.sort(key=lambda r: (-r["reconnected_origins"], -r["distance_saved_m_for_already_reachable"], r["reopened"]))
        return GeographicResult(analysis=result, pair_restorations=pairs, dataset=manifest,
            origins=origins, facilities=facilities,
            context=request.context, limitations=[
                "All closures are conditional hypothetical graph scenarios; no current road state is established.",
                "Distances are between snapped road nodes, not travel times or door-to-door access; facility capability is unverified.",
                "Incident coordinates validate study-area membership; analysis uses the selected cached grid origins, not a new incident-point route.",
                "The fixed 2026-10-24 OSM snapshot excludes external roads/hospitals; origins have equal weight.",
                "All parallel edges between both endpoint directions are removed; other carriageways are unaffected.",
                "Pairs are evaluated only if every individual reopening has zero benefit; at most six supplied closures (15 pairs).",
            ])

    def environment(self, request: EnvironmentRequest) -> EnvironmentResult:
        from lifelinetwin_geo.weather import load_observations, fetch_forecast, STUDY_AREA
        from lifelinetwin_geo.forecasting import TTMForecaster

        if request.mode == "cache":
            path = self.settings.weather_snapshot
            obs = load_observations(path.parent, path.stem.removeprefix("obs_"))
            if obs is None:
                raise ToolUnavailable("Configured Open-Meteo snapshot is missing")
            source_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            cache_file = path.name
        else:
            # The existing ingestion/parser is reused; no existing cache is overwritten.
            obs = fetch_forecast(past_days=30, forecast_days=1)
            source_digest = hashlib.sha256(json.dumps(obs, sort_keys=True).encode()).hexdigest()
            cache_file = None
        if request.as_of > datetime.now(timezone.utc):
            raise ValueError("as_of cannot be in the future")
        retrieved = utc(obs["retrieved_utc"])
        cutoff = min(utc(request.as_of), retrieved)
        times = obs["timestamps"]
        parsed = [utc(t) for t in times]
        if any(a >= b for a, b in zip(parsed, parsed[1:])):
            raise ToolUnavailable("Weather timestamps must be unique and chronological")
        indices = [i for i, t in enumerate(parsed) if t <= cutoff]
        if len(indices) < 512:
            raise ToolUnavailable("Fewer than 512 past hours at the requested as_of; no forecast was fabricated")
        if any((parsed[b] - parsed[a]).total_seconds() != 3600 for a, b in zip(indices, indices[1:])):
            raise ToolUnavailable("Weather context must be hourly and contiguous")
        filtered = {k: obs[k] for k in ("source", "retrieved_utc", "lat", "lon", "timezone")}
        filtered.update(timestamps=[times[i] for i in indices], n_hours=len(indices), variables={})
        for name, entry in obs["variables"].items():
            if len(entry["values"]) != len(times):
                raise ToolUnavailable("Weather values and timestamps have different lengths")
            filtered["variables"][name] = {"unit": entry["unit"], "values": [entry["values"][i] for i in indices]}
        snapshot = self.settings.model_cache / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots" / MODEL_REVISION
        if not (snapshot / "model.safetensors").is_file() or not (snapshot / "config.json").is_file():
            raise ToolUnavailable("Previously downloaded TTM model is missing; automatic model download is disabled")
        with self.model_lock:
            if self.forecaster is None:
                self.forecaster = TTMForecaster(model_id=str(snapshot))
            forecast = self.forecaster.predict(filtered, variable=request.variable)
        forecast["model_id"] = MODEL_ID
        forecast["model_revision"] = MODEL_REVISION
        forecast["forecast_timestamps"] = [utc(t).isoformat() for t in forecast["forecast_timestamps"]]
        for key in ("context_start", "context_end"):
            forecast["metadata"][key] = utc(forecast["metadata"][key]).isoformat()
        filtered["timestamps"] = [utc(t).isoformat() for t in filtered["timestamps"]]
        return EnvironmentResult(observations=filtered, forecast=forecast, provenance={
            "mode": request.mode, "source": obs["source"], "retrieved_utc": retrieved.isoformat(),
            "as_of": request.as_of.isoformat(), "context_cutoff_utc": cutoff.isoformat(),
            "snapshot_file": cache_file, "snapshot_sha256": source_digest,
            "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
            "model_weights_sha256": hashlib.sha256((snapshot / "model.safetensors").read_bytes()).hexdigest(),
            "product_type": "Open-Meteo forecast API recent-past model-derived estimates; not verified station measurements",
            "requested_location": {"latitude": STUDY_AREA["lat"], "longitude": STUDY_AREA["lon"]},
            "returned_grid_location": {"latitude": obs["lat"], "longitude": obs["lon"]},
            "excluded_future_hours": len(times) - len(indices),
            "weather_implies_road_closure": False,
        }, limitations=[
            "Open-Meteo recent-past estimates can be revised and are not verified road or station observations.",
            "Future forecast-API values are excluded from TTM context; hourly times are UTC.",
            "Cache mode is a historical snapshot replay, not current conditions or an as-issued historical forecast.",
            "One centroid weather grid represents the study area; incident coordinates do not change that grid.",
            "TTM is a zero-shot time-series extrapolation, not a calibrated meteorological or road-closure model.",
        ])
