"""Validated input and explicit evidence categories. Unknown fields are rejected."""
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from typing_extensions import TypedDict, NotRequired


class AccessibilityRow(TypedDict):
    id: str
    node: int
    distance_m: float | None
    facility_node: int | None
    path: list[int]


class DistanceChange(TypedDict):
    id: str
    baseline_m: float | None
    scenario_m: float | None
    newly_disconnected: bool
    increase_m: float | None


class ClosureOutput(TypedDict):
    id: str
    u: int
    v: int
    hypothetical: bool
    name: NotRequired[str]
    baseline_route_uses: NotRequired[int]
    betweenness_score: NotRequired[float]
    selection_method: NotRequired[str]


class RestorationOutput(TypedDict):
    reopened: str | list[str]
    reconnected_origins: int
    distance_saved_m_for_already_reachable: float
    accessibility: list[AccessibilityRow]


class GeographicAnalysis(TypedDict):
    baseline: list[AccessibilityRow]
    closures: list[ClosureOutput]
    disrupted: list[AccessibilityRow]
    changes: list[DistanceChange]
    restorations: list[RestorationOutput]


class VariableValues(TypedDict):
    unit: str
    values: list[float | None]


class ObservationsOutput(TypedDict):
    source: str
    retrieved_utc: str
    lat: float
    lon: float
    timezone: str
    timestamps: list[str]
    n_hours: int
    variables: dict[str, VariableValues]


class ForecastOutput(TypedDict):
    model_id: str
    model_revision: str
    method: str
    variable: str
    unit: str
    context_length_hours: int
    forecast_horizon_hours: int
    forecast_timestamps: list[str]
    forecast_values: list[float]
    variable_compatibility: dict[str, Any]
    metadata: dict[str, Any]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceKind(StrEnum):
    verified = "verified"
    user_reported = "user_reported"
    hypothetical = "hypothetical"


class IncidentStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"


class Context(Schema):
    latitude: float = Field(default=49.415, ge=49.395, le=49.435, allow_inf_nan=False)
    longitude: float = Field(default=8.6775, ge=8.650, le=8.705, allow_inf_nan=False)
    origin_ids: list[str] = Field(default_factory=list, max_length=9)

    @model_validator(mode="after")
    def unique_origins(self):
        if len(set(self.origin_ids)) != len(self.origin_ids):
            raise ValueError("Duplicate origin IDs")
        return self


class Claim(Schema):
    kind: EvidenceKind
    statement: str = Field(min_length=1, max_length=4000)
    source: str = Field(min_length=1, max_length=1000)
    observed_at: AwareDatetime
    verification_method: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def verified_attribution(self):
        if self.kind == EvidenceKind.verified and not self.verification_method:
            raise ValueError("Verified claims require a verification_method; this is submitter attribution")
        return self


class IncidentCreate(Schema):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    kind: EvidenceKind
    occurred_at: AwareDatetime
    context: Context = Field(default_factory=Context)
    claims: list[Claim] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def require_verified_claim(self):
        if self.kind == EvidenceKind.verified and not any(c.kind == EvidenceKind.verified for c in self.claims):
            raise ValueError("A verified incident requires at least one attributed verified claim")
        return self


class StatusUpdate(Schema):
    status: IncidentStatus


class Incident(IncidentCreate):
    id: str
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime


class Segment(Schema):
    id: str = Field(min_length=1, max_length=50)
    u: int = Field(strict=True)
    v: int = Field(strict=True)

    @model_validator(mode="after")
    def different_nodes(self):
        if self.u == self.v:
            raise ValueError("Segment endpoints must differ")
        return self


class GeographicRequest(Schema):
    context: Context = Field(default_factory=Context)
    selection: Literal["provided", "betweenness"] = "provided"
    closures: list[Segment] = Field(default_factory=list, max_length=6)
    count: int = Field(default=3, ge=1, le=6)

    @model_validator(mode="after")
    def validate_segments(self):
        if self.selection == "betweenness" and self.closures:
            raise ValueError("Use either provided closures or betweenness selection")
        if len({s.id for s in self.closures}) != len(self.closures):
            raise ValueError("Duplicate closure IDs")
        if len({tuple(sorted((s.u, s.v))) for s in self.closures}) != len(self.closures):
            raise ValueError("Duplicate closure segments")
        return self


class EnvironmentRequest(Schema):
    mode: Literal["cache", "live"] = "cache"
    variable: Literal["temperature_2m", "precipitation", "wind_speed_10m", "surface_pressure", "relative_humidity_2m"] = "temperature_2m"
    as_of: AwareDatetime


class InvestigationRequest(EnvironmentRequest):
    selection: Literal["provided", "betweenness"] = "provided"
    closures: list[Segment] = Field(default_factory=list, max_length=6)
    count: int = Field(default=3, ge=1, le=6)


class EnvironmentResult(Schema):
    observations: ObservationsOutput
    forecast: ForecastOutput
    provenance: dict[str, Any]
    limitations: list[str]


class GeographicResult(Schema):
    scenario_type: Literal["hypothetical"] = "hypothetical"
    analysis: GeographicAnalysis
    pair_restorations: list[RestorationOutput]
    dataset: dict[str, Any]
    origins: list[dict[str, Any]]
    facilities: list[dict[str, Any]]
    context: Context
    limitations: list[str]


class Recommendation(Schema):
    action: str
    evidence_refs: list[str]
    conditional: bool = True


class InvestigationResult(Schema):
    pipeline: Literal["deterministic_tools_phase4a"] = "deterministic_tools_phase4a"
    incident_snapshot: Incident
    request: InvestigationRequest
    environment: EnvironmentResult
    geography: GeographicResult
    evidence: list[dict[str, Any]]
    assumptions: list[str]
    limitations: list[str]
    recommendations: list[Recommendation]
    scenario_memory: dict[str, Any] | None = None


class Investigation(Schema):
    id: str
    incident_id: str
    created_at: datetime
    status: Literal["completed", "failed"]
    request: InvestigationRequest
    result: InvestigationResult | None = None
    error: str | None = None


class ObservationRecord(Schema):
    id: str
    incident_id: str
    investigation_id: str
    category: Literal["environmental_product"]
    payload: EnvironmentResult


class Health(Schema):
    status: Literal["ok"]
    database: Literal["ok"]
    pipeline: Literal["deterministic_tools_phase4a"]
    geographic_cache_present: bool
    model_cache_present: bool
