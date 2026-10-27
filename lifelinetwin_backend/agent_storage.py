"""Additive tables and per-event durable checkpoints; Phase 4A tables unchanged."""
from sqlalchemy import ForeignKey, JSON, String, Integer, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, uid, now
from .agent_schemas import AgentRun, AgentTrace


class AgentRunRow(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)
    status: Mapped[str] = mapped_column(String, default="running")
    request: Mapped[dict] = mapped_column(JSON)
    model_identity: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentTraceRow(Base):
    __tablename__ = "agent_traces"
    __table_args__ = (UniqueConstraint("run_id", "sequence"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=now)
    payload: Mapped[dict] = mapped_column(JSON)


def run_view(row):
    return AgentRun(**{name: getattr(row, name) for name in AgentRun.model_fields})


def recover_interrupted(db):
    # Single-worker local application: never silently replay an API request or spend tokens twice.
    with db.sessions.begin() as session:
        for row in session.scalars(select(AgentRunRow).where(AgentRunRow.status == "running")):
            row.status = "interrupted"
            row.updated_at = now()
            row.error = "Backend restarted; durable tool evidence retained. Automatic LLM replay is disabled."
