"""Agent endpoints are additive; Phase 4A behavior and response contracts remain intact."""
from threading import Lock
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from .agent import AgentRunner
from .agent_provider import ProviderConfig, ProviderConfigurationError, OpenAICompatibleProvider
from .agent_schemas import AgentRequest, AgentRun, AgentTrace
from .agent_storage import AgentRunRow, AgentTraceRow, run_view
from .database import IncidentRow
from .schemas import Incident


def agent_router(db, settings, provider_factory=None):
    router = APIRouter(tags=["Phase 4B agent investigations"])
    run_lock = Lock()

    def incident_exists(session, incident_id):
        row = session.get(IncidentRow, str(incident_id))
        if row is None:
            raise HTTPException(404, "Incident not found")
        return row

    @router.post("/incidents/{incident_id}/agent-investigations", response_model=AgentRun, status_code=201)
    def create_run(incident_id: UUID, body: AgentRequest):
        with db.sessions() as session:
            row = incident_exists(session, incident_id)
            incident = Incident(**row.payload, id=row.id, status=row.status, created_at=row.created_at, updated_at=row.updated_at)
        try:
            provider = provider_factory() if provider_factory else OpenAICompatibleProvider(ProviderConfig.from_environment())
        except ProviderConfigurationError as exc:
            raise HTTPException(503, {"code": "llm_not_configured", "message": str(exc)}) from exc
        if not run_lock.acquire(blocking=False):
            raise HTTPException(429, "Another agent investigation is running in this local worker")
        try:
            return AgentRunner(db, settings, incident, body, provider).run()
        finally:
            run_lock.release()

    @router.get("/incidents/{incident_id}/agent-investigations", response_model=list[AgentRun])
    def list_runs(incident_id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.sessions() as session:
            incident_exists(session, incident_id)
            return [run_view(row) for row in session.scalars(select(AgentRunRow).where(AgentRunRow.incident_id == str(incident_id))
                    .order_by(AgentRunRow.created_at, AgentRunRow.id).offset(offset).limit(limit))]

    @router.get("/agent-investigations/{run_id}", response_model=AgentRun)
    def get_run(run_id: UUID):
        with db.sessions() as session:
            row = session.get(AgentRunRow, str(run_id))
            if row is None:
                raise HTTPException(404, "Agent investigation not found")
            return run_view(row)

    @router.get("/agent-investigations/{run_id}/trace", response_model=list[AgentTrace])
    def get_trace(run_id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.sessions() as session:
            if session.get(AgentRunRow, str(run_id)) is None:
                raise HTTPException(404, "Agent investigation not found")
            return [AgentTrace(sequence=r.sequence, kind=r.kind, created_at=r.created_at, payload=r.payload)
                    for r in session.scalars(select(AgentTraceRow).where(AgentTraceRow.run_id == str(run_id))
                        .order_by(AgentTraceRow.sequence).offset(offset).limit(limit))]

    return router
