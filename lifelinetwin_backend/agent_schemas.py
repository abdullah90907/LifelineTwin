"""Agent input contracts and evidence-bound output: no model-authored measurements."""
from typing import Any, Literal
from pydantic import Field, model_validator
from .schemas import Schema, EnvironmentRequest, Segment, GeographicRequest


class AgentRequest(EnvironmentRequest):
    question: str = Field(min_length=1, max_length=4000)
    allowed_closures: list[Segment] = Field(default_factory=list, max_length=6)
    max_iterations: int = Field(default=6, ge=1, le=10)
    max_tool_calls: int = Field(default=12, ge=1, le=20)
    timeout_seconds: int = Field(default=120, ge=5, le=300)
    tool_timeout_seconds: int = Field(default=45, ge=1, le=60)

    @model_validator(mode="after")
    def approved_scenarios(self):
        GeographicRequest(closures=self.allowed_closures)
        return self


class EmptyInput(Schema):
    pass


class ClosureInput(Schema):
    closure_ids: list[str] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique(self):
        if len(self.closure_ids) != len(set(self.closure_ids)):
            raise ValueError("Duplicate closure IDs")
        return self


class Citation(Schema):
    evidence_id: str = Field(min_length=1, max_length=60)
    pointer: str = Field(default="", max_length=300, description="RFC6901 JSON pointer into successful tool output")


class EvidenceQuery(Citation):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=8, ge=1, le=32)
    text_offset: int = Field(default=0, ge=0)
    text_limit: int = Field(default=512, ge=1, le=1200)


UNCERTAINTIES = {
    "road_status_unverified": "Road status requires independent human/authority verification; all modeled closures are hypothetical.",
    "historical_snapshot": "Historical cached data do not establish current conditions or an as-issued historical forecast.",
    "weather_not_causal": "Environmental estimates and predictions do not establish closure, damage, or causation.",
    "distance_only": "Routing measures snapped-node network distance, not travel time or operational hospital capability.",
    "evidence_unavailable": "Some requested evidence was not obtained; inspect tool errors and the recorded question.",
}


class ActionSelection(Schema):
    kind: Literal["verify_road_status", "review_environment", "evaluate_restoration", "collect_missing_evidence"]
    citations: list[Citation] = Field(min_length=1, max_length=5)


class FinalSelection(Schema):
    findings: list[Citation] = Field(min_length=1, max_length=12)
    uncertainties: list[Literal["road_status_unverified", "historical_snapshot", "weather_not_causal", "distance_only", "evidence_unavailable"]] = Field(min_length=1, max_length=5)
    actions: list[ActionSelection] = Field(min_length=1, max_length=6)


class AgentFinding(Schema):
    citation: Citation
    evidence_category: str
    value: Any
    statement: str


class AgentAction(Schema):
    action: str
    citations: list[Citation]
    human_review_required: Literal[True] = True


class AgentResult(Schema):
    pipeline: Literal["langgraph_llm_tools_phase4b"] = "langgraph_llm_tools_phase4b"
    findings: list[AgentFinding]
    uncertainties: list[str]
    recommendations: list[AgentAction]
    evidence_ids: list[str]
    unavailable_evidence: list[dict[str, str]] = Field(default_factory=list)
    limitations: list[str]


class AgentRun(Schema):
    id: str
    incident_id: str
    created_at: str
    updated_at: str
    status: Literal["running", "completed", "failed", "limited", "interrupted"]
    request: AgentRequest
    model_identity: dict[str, Any]
    result: AgentResult | None
    error: str | None
    iterations: int
    tool_calls: int


class AgentTrace(Schema):
    sequence: int
    kind: str
    created_at: str
    payload: dict[str, Any]
