"""Evidence-backed orchestration without an LLM, agent loop, or inferred closures."""
from .schemas import (GeographicRequest, InvestigationRequest, InvestigationResult,
                      Incident, Recommendation)
from .scenario_memory import project_scenario


def investigate(incident: Incident, request: InvestigationRequest, tools) -> InvestigationResult:
    geo_request = GeographicRequest(context=incident.context, selection=request.selection,
                                    closures=request.closures, count=request.count)
    geography = tools.geographic(geo_request)
    environment = tools.environment(request)
    alternatives = geography.pair_restorations or geography.analysis["restorations"]
    best = max(alternatives, key=lambda r: (r["reconnected_origins"],
               r["distance_saved_m_for_already_reachable"]), default=None)
    recommendations = [Recommendation(
        action="Verify reported road conditions with the responsible authority before any operational action; forecasts do not verify closures.",
        evidence_refs=["incident", "environment"])]
    if best and (best["reconnected_origins"] or best["distance_saved_m_for_already_reachable"] > 1e-8):
        recommendations.append(Recommendation(
            action=f"In this hypothetical scenario, evaluate reopening {best['reopened']}: "
                   f"reconnects {best['reconnected_origins']} origin(s), saving "
                   f"{best['distance_saved_m_for_already_reachable']:.3f} origin-metres among already reachable origins.",
            evidence_refs=["geography"]))
    else:
        recommendations.append(Recommendation(
            action="No evaluated restoration shows a measurable accessibility benefit for the selected origins; do not infer that the roads are unimportant.",
            evidence_refs=["geography"]))
    return InvestigationResult(incident_snapshot=incident, request=request,
        scenario_memory=project_scenario(incident.id, geography.analysis["closures"], best),
        environment=environment, geography=geography, recommendations=recommendations,
        evidence=[
            {"id": "incident", "kind": incident.kind, "source": "API submission",
             "claims": [c.model_dump(mode="json") for c in incident.claims],
             "note": "Verified is a submitter-supplied attribution, not independent backend certification."},
            {"id": "geography", "kind": "computed_hypothetical", "source": geography.dataset,
             "method": "Existing NetworkX distance engine; independent and conditional pair reopening comparisons"},
            {"id": "environment", "kind": "model_derived_environmental_data_and_prediction",
             "source": environment.provenance},
        ], assumptions=[
            "Provided closure endpoint pairs define a hypothetical scenario regardless of incident claim classification.",
            "Environmental output never changes the graph or selects closures.",
            "All selected origins have equal weight; restoration comparisons retain all other closures.",
        ], limitations=geography.limitations + environment.limitations + [
            "Deterministic synchronous tool pipeline; no autonomous LLM agent or operational authority.",
            "No restoration costs, capacity, travel-time, hydraulic model, or causal incident attribution.",
        ])
