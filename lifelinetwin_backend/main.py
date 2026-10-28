"""FastAPI application factory. Start with uvicorn lifelinetwin_backend.main:app."""
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select, text

from .config import Settings
from .database import Database, IncidentRow, InvestigationRow, ObservationRow, RecommendationRow, now
from .investigation import investigate
from .schemas import (Health, IncidentCreate, Incident, StatusUpdate, Investigation,
                      InvestigationRequest, GeographicRequest, GeographicResult,
                      EnvironmentRequest, EnvironmentResult, ObservationRecord, Recommendation)
from .services import Tools, ToolUnavailable, MODEL_ID, MODEL_REVISION

logger = logging.getLogger(__name__)


def incident_view(row):
    return Incident(**row.payload, id=row.id, status=row.status,
                    created_at=row.created_at, updated_at=row.updated_at)


def investigation_view(row):
    return Investigation(id=row.id, incident_id=row.incident_id, created_at=row.created_at,
                         status=row.status, request=row.request, result=row.result, error=row.error)


def create_app(settings: Settings | None = None, tools=None, agent_provider_factory=None) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings.database_path)
    tools = tools or Tools(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        from .agent_storage import recover_interrupted
        recover_interrupted(db)
        yield
        db.engine.dispose()

    app = FastAPI(title="LifelineTwin Phase 4A", version="0.4.0", lifespan=lifespan,
                  description="Local deterministic research workflow. All road closures are hypothetical graph scenarios; weather never establishes road state.")
    app.state.database = db
    app.state.tools = tools

    def get_incident(session, incident_id):
        row = session.get(IncidentRow, str(incident_id))
        if row is None:
            raise HTTPException(404, "Incident not found")
        return row

    @app.get("/health", response_model=Health)
    def health():
        with db.sessions() as session:
            session.execute(text("SELECT 1"))
        model = settings.model_cache / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots" / MODEL_REVISION
        return Health(status="ok", database="ok", pipeline="deterministic_tools_phase4a",
                      geographic_cache_present=(settings.geographic_cache / "manifest.json").is_file(),
                      model_cache_present=(model / "model.safetensors").is_file())

    @app.post("/incidents", response_model=Incident, status_code=201)
    def create_incident(body: IncidentCreate):
        with db.sessions.begin() as session:
            row = IncidentRow(payload=body.model_dump(mode="json"))
            session.add(row)
            session.flush()
            return incident_view(row)

    @app.get("/incidents", response_model=list[Incident])
    def incidents(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.sessions() as session:
            return [incident_view(row) for row in session.scalars(select(IncidentRow)
                    .order_by(IncidentRow.created_at, IncidentRow.id).offset(offset).limit(limit))]

    @app.get("/incidents/{incident_id}", response_model=Incident)
    def get_one(incident_id: UUID):
        with db.sessions() as session:
            return incident_view(get_incident(session, incident_id))

    @app.patch("/incidents/{incident_id}/status", response_model=Incident)
    def update_status(incident_id: UUID, body: StatusUpdate):
        with db.sessions.begin() as session:
            row = get_incident(session, incident_id)
            row.status = body.status.value
            row.updated_at = now()
            session.flush()
            return incident_view(row)

    @app.get("/incidents/{incident_id}/investigations", response_model=list[Investigation])
    def history(incident_id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.sessions() as session:
            get_incident(session, incident_id)
            return [investigation_view(row) for row in session.scalars(select(InvestigationRow)
                    .where(InvestigationRow.incident_id == str(incident_id))
                    .order_by(InvestigationRow.created_at, InvestigationRow.id).offset(offset).limit(limit))]

    @app.get("/investigations/{investigation_id}", response_model=Investigation)
    def investigation_by_id(investigation_id: UUID):
        with db.sessions() as session:
            row = session.get(InvestigationRow, str(investigation_id))
            if row is None:
                raise HTTPException(404, "Investigation not found")
            return investigation_view(row)

    @app.post("/incidents/{incident_id}/investigations", response_model=Investigation, status_code=201)
    def run_investigation(incident_id: UUID, body: InvestigationRequest):
        # Materialize the incident snapshot before expensive work; no DB transaction is held during inference.
        with db.sessions() as session:
            incident = incident_view(get_incident(session, incident_id))
        try:
            GeographicRequest(context=incident.context, selection=body.selection,
                              closures=body.closures, count=body.count)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        if body.selection == "betweenness" and incident.kind != "hypothetical":
            raise HTTPException(422, "Automatic stress-test selection requires a hypothetical incident; provide explicit scenario segments otherwise")
        result = None
        failure = None
        error_code = 503
        try:
            result = investigate(incident, body, tools)
            # Reject non-finite or non-serializable tool values before the transaction.
            import json
            json.dumps(result.model_dump(mode="json"), allow_nan=False)
        except Exception as exc:
            logger.exception("Investigation tool failure")
            error_code = 422 if isinstance(exc, ValueError) else 503
            failure = str(exc) if isinstance(exc, (ValueError, ToolUnavailable)) else "A required investigation tool failed; see backend logs"
        with db.sessions.begin() as session:
            row = InvestigationRow(incident_id=str(incident_id), request=body.model_dump(mode="json"),
                                   status="failed" if failure else "completed",
                                   result=result.model_dump(mode="json") if not failure else None, error=failure)
            session.add(row)
            session.flush()
            if not failure:
                session.add(ObservationRow(incident_id=str(incident_id), investigation_id=row.id,
                                          category="environmental_product", payload=result.environment.model_dump(mode="json")))
                session.add_all(RecommendationRow(investigation_id=row.id, payload=r.model_dump(mode="json"))
                                for r in result.recommendations)
            response = investigation_view(row)
        if failure:
            raise HTTPException(error_code, {"investigation_id": response.id, "error": failure})
        return response

    @app.get("/incidents/{incident_id}/observations", response_model=list[ObservationRecord])
    def observations(incident_id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.sessions() as session:
            get_incident(session, incident_id)
            return [ObservationRecord(id=r.id, incident_id=r.incident_id, investigation_id=r.investigation_id,
                                      category=r.category, payload=r.payload)
                    for r in session.scalars(select(ObservationRow).where(ObservationRow.incident_id == str(incident_id))
                                             .order_by(ObservationRow.id).offset(offset).limit(limit))]

    @app.get("/investigations/{investigation_id}/recommendations", response_model=list[Recommendation])
    def recommendations(investigation_id: UUID):
        with db.sessions() as session:
            if session.get(InvestigationRow, str(investigation_id)) is None:
                raise HTTPException(404, "Investigation not found")
            return [Recommendation(**row.payload) for row in session.scalars(select(RecommendationRow)
                    .where(RecommendationRow.investigation_id == str(investigation_id)).order_by(RecommendationRow.id))]

    def run_tool(method, body):
        try:
            return method(body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            logger.exception("Analysis tool failure")
            detail = str(exc) if isinstance(exc, ToolUnavailable) else "Required cached data/model or external service unavailable"
            raise HTTPException(503, detail) from exc

    @app.get("/analysis/baseline", response_model=GeographicResult)
    def baseline():
        return run_tool(tools.geographic, GeographicRequest())

    @app.post("/analysis/geographic", response_model=GeographicResult)
    def geographic(body: GeographicRequest):
        return run_tool(tools.geographic, body)

    @app.post("/analysis/environment", response_model=EnvironmentResult)
    def environment(body: EnvironmentRequest):
        return run_tool(tools.environment, body)

    @app.get("/weather/current")
    def weather_current():
        from .live_weather import current_weather
        try:
            return current_weather()
        except Exception:
            logger.exception('Current weather provider unavailable')
            raise HTTPException(503, 'Current weather is unavailable. Retry later; no historical values were substituted.')

    @app.get('/weather/alerts')
    def weather_alerts():
        from .live_weather import active_alerts
        try:
            return active_alerts()
        except Exception:
            logger.exception('NWS alerts unavailable')
            raise HTTPException(503,'NWS alert service unavailable. Absence of data does not mean absence of hazards.')

    from .agent_api import agent_router
    app.include_router(agent_router(db, settings, agent_provider_factory))
    return app


app = create_app()
