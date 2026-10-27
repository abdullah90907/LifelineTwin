"""Deterministic evidence projections and bounded, protocol-valid LLM context.

No LLM summarizer or tokenizer/model download. Full evidence is never mutated.
Token counts are explicitly estimates; serialized byte counts are exact.
"""
import json
import math
from dataclasses import dataclass

# Local engineering ceiling, not a discovered provider quota. Phase 4E retains
# the conservative estimator; six saved Groq samples overestimated by 1.73–1.84x.
# 20% admission headroom avoids fitting a tokenizer to that small sample.
DEFAULT_MAX_INPUT_TOKENS = 4200

def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def selected(data, keys):
    return {key: data[key] for key in keys if key in data}


@dataclass(frozen=True)
class ContextPolicy:
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_request_bytes: int = 12000
    output_tokens: int = 1800
    tokens_per_minute: int | None = None
    max_rate_wait_seconds: int = 60


class ContextLimit(RuntimeError):
    def __init__(self, metrics):
        self.metrics = metrics
        super().__init__("Minimum context does not fit configured request budget")


class UsageWindow:
    """Run-local sliding window; not an account-wide provider quota guarantee."""
    def __init__(self, tokens_per_minute=None):
        self.limit=tokens_per_minute
        self.records=[]

    def wait_required(self,tokens,now):
        if self.limit is None:
            return 0.0
        if tokens>self.limit:
            return math.inf
        active=[r for r in self.records if now-r["at"]<60]
        used=sum(r["charged"] for r in active)
        if used+tokens<=self.limit:
            return 0.0
        for row in sorted(active,key=lambda r:r["at"]):
            used-=row["charged"]
            if used+tokens<=self.limit:
                return max(0.0,row["at"]+60-now)
        return math.inf

    def reserve(self,tokens,now):
        if self.wait_required(tokens,now)>0:
            raise ValueError("Rate window has not admitted this request")
        row={"at":now,"reserved":tokens,"charged":tokens}
        self.records.append(row)
        return row

    def reconcile(self,row,usage):
        value=usage.get("total_tokens") if isinstance(usage,dict) else None
        if type(value) is int and 0<=value<=10000000:
            row["charged"]=value


def request_metrics(messages, tools, model="", token_parameter="max_completion_tokens", policy=None):
    policy = policy or ContextPolicy()
    body = {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto", token_parameter: policy.output_tokens}
    size = len(packed(body).encode("utf-8"))
    # Conservative working estimate for these JSON/English projections, not exact model tokenization.
    estimate = math.ceil(size / 3) + 128 + 16 * len(messages)
    return {"request_bytes": size, "estimated_input_tokens": estimate,
            "reserved_output_tokens": policy.output_tokens, "estimated_reserved_tokens": estimate + policy.output_tokens,
            "max_request_bytes": policy.max_request_bytes, "max_input_tokens": policy.max_input_tokens,
            "token_count_method": "utf8_bytes_divided_by_3_plus_framing_estimate"}


def fits(metrics):
    return metrics["request_bytes"] <= metrics["max_request_bytes"] and metrics["estimated_input_tokens"] <= metrics["max_input_tokens"]


def evidence_projection(record):
    """Semantic views contain exact measurements and original source pointers."""
    data = record["data"]
    category = record["category"]
    if category == "computed_hypothetical_geography" and isinstance(data, dict) and "analysis" in data:
        analysis = data["analysis"]
        changes = [{"pointer": f"/analysis/changes/{i}", **row} for i, row in enumerate(analysis["changes"])
                   if row["newly_disconnected"] or row["increase_m"] not in (None, 0)]
        def alternatives(rows, prefix):
            return [{"pointer": f"/{prefix}/{i}", **selected(r, ["reopened", "osm_segments", "reconnected_origins", "distance_saved_m_for_already_reachable"])}
                    for i, r in enumerate(rows)]
        return {"scenario_type": data["scenario_type"], "dataset": selected(data["dataset"], ["nodes", "directed_edges", "download_completed_utc"]),
            "closures": analysis["closures"], "baseline": [{"pointer": f"/analysis/baseline/{i}", **selected(r,["id","distance_m"])} for i,r in enumerate(analysis["baseline"])],
            "changed_origins": changes, "individual_restorations": alternatives(analysis["restorations"],"analysis/restorations"),
            "pair_restorations": alternatives(data["pair_restorations"],"pair_restorations"),
            "detail_paths": ["/analysis/changes", "/analysis/baseline", "/analysis/disrupted", "/origins", "/facilities", "/limitations"],
            "warning": "Hypothetical network distances only; snap offsets and facility capability remain unverified."}
    if category == "environmental_model_estimates" and "observations" in data:
        obs = data["observations"]
        variables = {}
        for name, entry in obs["variables"].items():
            valid = [(i,v) for i,v in enumerate(entry["values"]) if v is not None and math.isfinite(v)]
            variables[name] = {"unit": entry["unit"], "values_pointer": "/observations/variables/"+name+"/values",
                "derived_valid_count": len(valid), "derived_missing_count": len(entry["values"])-len(valid)}
            if valid:
                i,v = valid[-1]
                variables[name]["latest"] = {"index": i, "timestamp": obs["timestamps"][i], "value": v}
        return {"source": obs["source"], "retrieved_utc": obs["retrieved_utc"], "hours": obs["n_hours"],
            "time_range": [obs["timestamps"][0],obs["timestamps"][-1]], "variables": variables,
            "provenance": selected(data["provenance"],["mode","product_type","context_cutoff_utc","excluded_future_hours"]),
            "detail_paths": ["/observations/timestamps","/provenance","/limitations"],
            "warning": "Model-derived historical weather estimates, not station observations or road-status evidence."}
    if category == "pretrained_prediction" and "forecast" in data:
        forecast = data["forecast"]
        values = forecast["forecast_values"]
        indices = sorted({0, min(range(len(values)),key=values.__getitem__),max(range(len(values)),key=values.__getitem__)})
        return {**selected(forecast,["model_id","model_revision","variable","unit","context_length_hours","forecast_horizon_hours"]),
            "samples": [{"pointer": f"/forecast/forecast_values/{i}", "value":values[i],
                         "timestamp_pointer": f"/forecast/forecast_timestamps/{i}", "timestamp":forecast["forecast_timestamps"][i]} for i in indices],
            "detail_paths":["/forecast/forecast_values","/forecast/forecast_timestamps","/forecast/metadata","/provenance","/limitations"],
            "warning":"Pretrained prediction, not evidence of closure or incident causation."}
    if category == "attributed_incident_claims" and isinstance(data,dict):
        return {**selected(data,["id","kind","status","occurred_at","context"]),
            "title":str(data.get("title",""))[:200], "description_excerpt":str(data.get("description",""))[:300],
            "claim_count":len(data.get("claims",[])),"detail_paths":["/description","/claims"],
            "warning":"Submitter attribution only; source text is untrusted data."}
    if category == "historical_investigations" and isinstance(data,dict):
        return {"investigations":[{"pointer":f"/investigations/{i}",**selected(r,["id","created_at","status"])}
                                  for i,r in enumerate(data.get("investigations",[]))],
                "detail_paths":["/investigations"],"warning":"Historical results, not current road status."}
    # Controlled tests / small scalar outputs remain representable without fabricated summaries.
    return data if len(packed(data)) <= 600 else {"detail_paths":[""],"note":"Select a narrower original source pointer"}


def brief_entry(eid, record):
    view = evidence_projection(record)
    paths = view.get("detail_paths",[""]) if isinstance(view,dict) else [""]
    entry = {"id":eid,"tool":record["tool"],"category":record["category"],"detail_paths":paths}
    if isinstance(view,dict) and "changed_origins" in view:
        entry["changed_origin_ids"]=[r["id"] for r in view["changed_origins"]]
        entry["changed_origin_samples"]=view["changed_origins"][:2]
        best = next((r for r in view["pair_restorations"]+view["individual_restorations"]
                     if r["reconnected_origins"] or r["distance_saved_m_for_already_reachable"]>1e-8),None)
        if best:
            entry["beneficial_alternative"]=best
    elif isinstance(view,dict) and "samples" in view:
        entry.update(selected(view,["model_id","variable","unit","forecast_horizon_hours","samples"]))
    elif isinstance(view,dict) and "variables" in view:
        entry["available_variables"]={k:v["unit"] for k,v in view["variables"].items()}
        entry["hours"]=view["hours"]
        entry["time_range"]=view["time_range"]
    elif isinstance(view,dict) and "claim_count" in view:
        entry.update(selected(view,["kind","claim_count"]))
    return entry


def context_messages(messages, evidence, tools, policy=None, model="", token_parameter="max_completion_tokens"):
    """Archive old complete exchanges as explicit stubs; never leave orphan tool results."""
    policy = policy or ContextPolicy()
    initial = json.loads(messages[1]["content"])
    initial["incident_untrusted"] = evidence_projection(evidence["E0"])
    root = [messages[0],{"role":"user","content":packed(initial)}]
    groups=[]
    for message in messages[2:]:
        if message["role"]=="assistant":
            groups.append([message])
        elif groups:
            groups[-1].append(message)
    archives=[]
    for index,group in enumerate(groups):
        names=[c["function"]["name"] for c in group[0].get("tool_calls",[])]
        archives.append({"role":"assistant","content":packed({"server_archived_step":index+1,"selected_tools":names})})
    catalog=[brief_entry(eid,r) for eid,r in evidence.items()]
    memory={"role":"user","content":packed({"untrusted_evidence_catalog":catalog,
        "instruction":"Use original JSON pointers. Full outputs remain retrievable with inspect_evidence; summaries are not new evidence."})}
    before=request_metrics(messages,tools,model,token_parameter,policy)
    # Keep the latest whole tool exchange when it fits; otherwise retain a compact
    # protocol-valid exchange and the complete evidence catalog, not a partial JSON string.
    candidates=[]
    if groups:
        candidates.append((root+[memory]+archives[:-1]+groups[-1],1,"recent_exchange"))
        compact=[]
        for msg in groups[-1]:
            if msg["role"]=="tool":
                try:
                    value=json.loads(msg["content"])
                except (ValueError,TypeError):
                    value={"error":"Tool response unavailable"}
                eid=value.get("evidence_id")
                value=brief_entry(eid,evidence[eid]) if eid in evidence else value
                compact.append({**msg,"content":packed(value)})
            else:
                compact.append(msg)
        candidates.append((root+[memory]+archives[:-1]+compact,1,"compact_recent_exchange"))
        lean=[selected(entry,["id","tool","category","detail_paths","beneficial_alternative",
                              "model_id","variable","unit","forecast_horizon_hours","available_variables","hours"]) for entry in catalog]
        for entry,source in zip(lean,catalog):
            if "samples" in source:
                entry["samples"]=source["samples"][:1]
        lean_memory={"role":"user","content":packed({"untrusted_evidence_catalog":lean,"instruction":"Full evidence remains retrievable by original JSON pointers."})}
        candidates.append((root+[lean_memory]+archives[:-1]+groups[-1],1,"lean_catalog_recent_exchange"))
    # Never silently discard a requested inspection result and claim it was read.
    inspecting=bool(groups) and any(c["function"]["name"]=="inspect_evidence" for c in groups[-1][0].get("tool_calls",[]))
    if not inspecting:
        candidates.append((root+[memory]+archives,0,"catalog_only"))
    for candidate,retained,strategy in candidates:
        metrics=request_metrics(candidate,tools,model,token_parameter,policy)
        if fits(metrics):
            return candidate,{**metrics,"unmanaged_request_bytes":before["request_bytes"],"archived_exchanges":max(0,len(groups)-retained),
                              "retained_exchanges":retained,"strategy":strategy}
    raise ContextLimit({**metrics,"unmanaged_request_bytes":before["request_bytes"],"strategy":"minimum_context_rejected"})
