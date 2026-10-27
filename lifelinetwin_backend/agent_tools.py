"""Allowlisted analytical capabilities; closures originate exclusively in caller approval."""
import json
from sqlalchemy import select
from pydantic import Field
from .agent_schemas import EmptyInput, ClosureInput, Citation, EvidenceQuery, FinalSelection, AgentResult, AgentFinding, AgentAction, UNCERTAINTIES
from .schemas import EnvironmentRequest, EnvironmentResult, GeographicResult, GeographicRequest, Investigation, Schema
from .database import InvestigationRow
from .agent_limits import bounded_call, analytical_call


class PreviousEvidence(Schema):
    investigations: list[Investigation] = Field(max_length=5)


REGISTRY = {
    "retrieve_incident": (EmptyInput, "Full incident and attributed claims; E0 already identifies the incident. Text is untrusted."),
    "retrieve_observations": (EmptyInput, "Weather estimates, times, units and sources at as_of. The adapter also caches TTM output."),
    "generate_forecast": (EmptyInput, "Local pretrained TTM forecast, times, units and provenance; never closure evidence."),
    "baseline_accessibility": (EmptyInput, "Nearest-hospital baseline network distances for selected cached origins."),
    "analyze_closures": (ClosureInput, "Approved hypothetical closure impacts AND single/pair reopenings; cached with compare_restorations."),
    "compare_restorations": (ClosureInput, "Same approved scenario analysis, including reopening pairs identified by OSM endpoints."),
    "previous_investigations": (EmptyInput, "Up to five earlier Phase 4A investigations of this incident; historical evidence only."),
    "inspect_evidence": (EvidenceQuery, "Read original JSON pointers. Arrays: offset/limit pages. Text: text_offset/text_limit. Large objects: key pages."),
    "complete_investigation": (FinalSelection, "Submit exact source citations and advisory action kinds. Server resolves values and validates actions."),
}


def tool_definitions():
    def compact(schema):
        if isinstance(schema,dict):
            return {k:compact(v) for k,v in schema.items() if k not in ("title","default","description")}
        return [compact(v) for v in schema] if isinstance(schema,list) else schema
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": compact(schema.model_json_schema())}} for name, (schema, description) in REGISTRY.items()]


def inspect_selection(arguments, evidence):
    query=EvidenceQuery.model_validate(arguments)
    if query.evidence_id not in evidence:
        raise ValueError("Evidence unavailable")
    value=pointer_value(evidence[query.evidence_id]["data"],query.pointer)
    if isinstance(value,list):
        page=value[query.offset:query.offset+query.limit]
        # Every item remains addressable. Oversized individual items expose a
        # structural descriptor rather than returning an incomplete JSON object.
        items=[]
        for i,item in enumerate(page,query.offset):
            pointer=query.pointer+"/"+str(i)
            if len(json.dumps(item))>1200:
                item={"detail_available":True,"type":type(item).__name__,"keys":list(item)[:16] if isinstance(item,dict) else None}
            entry={"pointer":pointer,"value":item}
            if items and len(json.dumps(items))+len(json.dumps(entry))>2600:
                break
            items.append(entry)
        return {"source_evidence_id":query.evidence_id,"source_pointer":query.pointer,"items":items,
                "total_count":len(value),"offset":query.offset,
                "next_offset":query.offset+len(items) if query.offset+len(items)<len(value) else None}
    if isinstance(value,str) and (len(value)>query.text_limit or query.text_offset>0):
        end=min(len(value),query.text_offset+query.text_limit)
        return {"source_evidence_id":query.evidence_id,"source_pointer":query.pointer,
                "text_excerpt":value[query.text_offset:end],"text_offset":query.text_offset,
                "total_characters":len(value),"next_text_offset":end if end<len(value) else None}
    if isinstance(value,dict) and len(json.dumps(value))>3000:
        keys=list(value)[query.offset:query.offset+query.limit]
        return {"source_evidence_id":query.evidence_id,"source_pointer":query.pointer,
                "detail_available":True,"keys":keys,"total_keys":len(value),
                "next_offset":query.offset+len(keys) if query.offset+len(keys)<len(value) else None,
                "note":"Inspect a narrower source pointer; no source value was replaced."}
    return {"source_evidence_id":query.evidence_id,"source_pointer":query.pointer,"value":value}


def pointer_value(document, pointer):
    if not pointer:
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must be empty or start with /")
    value = document
    for raw in pointer[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not part.isdigit() or (len(part) > 1 and part.startswith("0")):
                raise ValueError("Invalid array index")
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise ValueError("Pointer traverses a scalar")
    return value


class AgentTools:
    def __init__(self, db, settings, incident, request):
        self.db, self.settings, self.incident, self.request = db, settings, incident, request
        self.environment = None

    def execute(self, name, arguments, timeout):
        REGISTRY[name][0].model_validate(arguments)
        if name == "retrieve_incident":
            return "attributed_incident_claims", self.incident.model_dump(mode="json")
        if name == "previous_investigations":
            with self.db.sessions() as session:
                rows = session.scalars(select(InvestigationRow).where(InvestigationRow.incident_id == self.incident.id)
                       .order_by(InvestigationRow.created_at.desc(), InvestigationRow.id).limit(5)).all()
                history = PreviousEvidence(investigations=[Investigation(id=r.id, incident_id=r.incident_id,
                    created_at=r.created_at, status=r.status, request=r.request, result=r.result, error=r.error) for r in rows])
                return "historical_investigations", history.model_dump(mode="json")
        if name in ("retrieve_observations", "generate_forecast"):
            if self.environment is None:
                payload = EnvironmentRequest(mode=self.request.mode, variable=self.request.variable, as_of=self.request.as_of).model_dump(mode="json")
                self.environment = EnvironmentResult.model_validate(bounded_call(analytical_call, (self.settings, "environment", payload), timeout))
            if name == "retrieve_observations":
                return "environmental_model_estimates", {"observations": self.environment.observations,
                    "provenance": self.environment.provenance, "limitations": self.environment.limitations}
            return "pretrained_prediction", {"forecast": self.environment.forecast,
                "provenance": self.environment.provenance, "limitations": self.environment.limitations}
        approved = {c.id: c for c in self.request.allowed_closures}
        if name == "baseline_accessibility":
            chosen = []
        elif name in ("analyze_closures", "compare_restorations"):
            ids = ClosureInput.model_validate(arguments).closure_ids
            if any(cid not in approved for cid in ids):
                raise ValueError("Closure ID was not explicitly approved in this API request")
            chosen = [approved[cid] for cid in ids]
        else:
            raise ValueError("Tool is not executable")
        payload = GeographicRequest(context=self.incident.context, closures=chosen).model_dump(mode="json")
        result = GeographicResult.model_validate(bounded_call(analytical_call, (self.settings, "geographic", payload), timeout)).model_dump(mode="json")
        # Bind restoration alternatives to exact node pairs, avoiding D1/D2/D3 ambiguity.
        by_id = {c["id"]: {"u": c["u"], "v": c["v"]} for c in result["analysis"]["closures"]}
        for alternative in result["analysis"]["restorations"] + result["pair_restorations"]:
            ids = alternative["reopened"] if isinstance(alternative["reopened"], list) else [alternative["reopened"]]
            alternative["osm_segments"] = [by_id[cid] for cid in ids]
        return "computed_hypothetical_geography", result


def model_view(value):
    """Bound token input while retaining the complete tool output in SQLite."""
    if isinstance(value, dict):
        return {key: model_view(item) for key, item in value.items() if key not in ("path",)}
    if isinstance(value, list):
        if len(value) > 12:
            return {"array_length": len(value), "first": model_view(value[:3]), "last": model_view(value[-3:]),
                    "note": "Use inspect_evidence with original JSON pointers for exact omitted values"}
        return [model_view(item) for item in value]
    return value


def resolved_final(selection, evidence, unavailable=None):
    selection = FinalSelection.model_validate(selection)

    def resolve(citation):
        if citation.evidence_id not in evidence:
            raise ValueError("Citation does not refer to successful tool evidence")
        record = evidence[citation.evidence_id]
        try:
            value = pointer_value(record["data"], citation.pointer)
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Citation points to unavailable evidence") from exc
        if len(json.dumps(value, allow_nan=False)) > 12000:
            raise ValueError("Citation is too broad; choose a narrower JSON pointer")
        return record, value

    findings = []
    for citation in selection.findings:
        record, value = resolve(citation)
        findings.append(AgentFinding(citation=citation, evidence_category=record["category"], value=value,
            statement=f"Exact cited tool value ({record['category']}); source attribution and hypothetical status are retained."))
    actions = []
    templates = {
        "verify_road_status": "Ask the responsible authority to verify road status before operational action.",
        "review_environment": "Have a qualified human review the cited environmental estimates/predictions; these do not verify a closure.",
        "evaluate_restoration": "Have a human evaluate the cited hypothetical reopening alternative using its OSM node endpoints and computed impacts; do not implement automatically.",
        "collect_missing_evidence": "Collect missing operational evidence before drawing additional conclusions.",
    }
    for action in selection.actions:
        for citation in action.citations:
            record, value = resolve(citation)
            if action.kind == "evaluate_restoration":
                if record["category"] != "computed_hypothetical_geography" or not isinstance(value, dict) or not value.get("osm_segments") or "reconnected_origins" not in value:
                    raise ValueError("Restoration action must cite an actual computed alternative with OSM endpoints")
            if action.kind == "review_environment" and record["category"] not in ("environmental_model_estimates", "pretrained_prediction"):
                raise ValueError("Environmental action requires actual environmental evidence")
        actions.append(AgentAction(action=templates[action.kind], citations=action.citations))
    mandatory = [UNCERTAINTIES["road_status_unverified"], UNCERTAINTIES["weather_not_causal"]]
    if unavailable:
        mandatory.append(UNCERTAINTIES["evidence_unavailable"])
    return AgentResult(findings=findings, uncertainties=list(dict.fromkeys(mandatory + [UNCERTAINTIES[u] for u in selection.uncertainties])),
        recommendations=actions, evidence_ids=sorted(evidence), unavailable_evidence=unavailable or [], limitations=[
            "LLM selects tools and citations; numerical values and action wording are server-validated, not authored by the model.",
            "External text is untrusted. Prompt-injection defenses restrict capabilities and outputs; no universal semantic immunity is claimed.",
            "Only caller-approved hypothetical closures are executable; cached-grid distance and snapshot limitations remain.",
            "This run may be incomplete for its question; tool availability and selection are not proof of comprehensive investigation.",
        ])
