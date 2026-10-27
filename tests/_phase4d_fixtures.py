"""Adaptive CONTROLLED provider for offline integration, never live LLM evidence."""
import json


def call(name,args,cid):
    return {"id":cid,"name":name,"arguments":json.dumps(args)}


class AdaptiveEvidenceProvider:
    secret=""
    identity={"adapter":"controlled_offline_phase4d","configured_model":"controlled-not-live","live_llm":False}

    def complete(self,messages,tools,timeout):
        initial=json.loads(messages[1]["content"])
        catalog=next(json.loads(m["content"])["untrusted_evidence_catalog"] for m in messages
                     if m["role"]=="user" and "untrusted_evidence_catalog" in m["content"])
        by_tool={e["tool"]:e for e in catalog}
        ids=[c["id"] for c in initial["allowed_hypothetical_closures"]]
        seen=[]
        for message in messages:
            if message["role"]=="assistant":
                seen.extend(c["function"]["name"] for c in message.get("tool_calls",[]))
                if not message.get("tool_calls"):
                    try:
                        seen.extend(json.loads(message["content"]).get("selected_tools",[]))
                    except (ValueError,TypeError):
                        pass
        env_missing="retrieve_observations" not in by_tool or "generate_forecast" not in by_tool
        geo_missing="analyze_closures" not in by_tool
        if env_missing:
            calls=[call("retrieve_observations",{},"obs"),call("generate_forecast",{},"fc")]
            if geo_missing and "weather first" not in initial["question"].lower():
                calls.insert(0,call("analyze_closures",{"closure_ids":ids},"geo"))
                if "repeat restoration" in initial["question"].lower():
                    calls.insert(1,call("compare_restorations",{"closure_ids":list(reversed(ids))},"repeat_geo"))
        elif geo_missing:
            calls=[call("analyze_closures",{"closure_ids":ids},"geo_after_weather")]
        elif "inspect_evidence" not in seen:
            geo=by_tool["analyze_closures"]
            # Follow up on a measured beneficial pair only when the catalog
            # actually reports one; no case-specific outcome is hardcoded.
            alternative=geo.get("beneficial_alternative")
            pointer=alternative["pointer"]+"/osm_segments" if alternative else "/analysis/changes"
            calls=[call("inspect_evidence",{"evidence_id":geo["id"],"pointer":pointer,"limit":2},"inspect_geo"),
                   call("inspect_evidence",{"evidence_id":by_tool["generate_forecast"]["id"],"pointer":"/forecast/forecast_values/0"},"inspect_prediction")]
        else:
            geo=by_tool["analyze_closures"]
            forecast=by_tool["generate_forecast"]
            observation=by_tool["retrieve_observations"]
            alt=geo.get("beneficial_alternative")
            inspected=[]
            prediction_seen=False
            for message in messages:
                if message['role']=='tool':
                    payload=json.loads(message['content']).get('data',{})
                    if isinstance(payload,dict) and payload.get('source_pointer','').endswith('/osm_segments'):
                        inspected=[item['value'] for item in payload.get('items',[])]
                    if isinstance(payload,dict) and payload.get('source_pointer')=='/forecast/forecast_values/0':
                        prediction_seen=isinstance(payload.get('value'),(int,float))
            if alt and (len(inspected)!=2 or not prediction_seen):
                # A controlled test failure, not a fabricated final answer.
                raise RuntimeError('Required inspection results were not available to the next model step')
            g={"evidence_id":geo["id"],"pointer":alt["pointer"] if alt else "/analysis/changes"}
            f={"evidence_id":forecast["id"],"pointer":"/forecast/forecast_values/0"}
            citations=[g,f,{"evidence_id":forecast["id"],"pointer":"/forecast/forecast_timestamps/0"},
                       {"evidence_id":observation["id"],"pointer":"/observations/variables/temperature_2m/values/0"}]
            actions=[{"kind":"evaluate_restoration" if alt else "verify_road_status","citations":[g]},
                     {"kind":"review_environment","citations":[f]}]
            calls=[call("complete_investigation",{"findings":citations,"uncertainties":["historical_snapshot","distance_only"],"actions":actions},"finish")]
        return {"model":"controlled-offline-not-live","note":"Controlled evidence-dependent test decision","calls":calls}
