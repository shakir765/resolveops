from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from resolveops_core.config import settings


class Base(DeclarativeBase):
    pass


class TicketStatus(str, Enum):
    NEW = "new"
    QUEUED = "queued"
    PROCESSING = "processing"
    TRIAGED = "triaged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    AWAITING_HUMAN = "awaiting_human"
    CLOSED = "closed"
    FAILED = "failed"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(64), default="api")
    status: Mapped[str] = mapped_column(String(32), default=TicketStatus.NEW.value, index=True)
    priority: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ticket_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    escalated: Mapped[bool] = mapped_column(default=False)
    external_ref: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    thread_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    current_step: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    state_version: Mapped[int] = mapped_column(default=0)
    prompt_version: Mapped[str] = mapped_column(String(16), default="v1")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_name: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_idempotency_tenant_key"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def new_id(prefix: str = "") -> str:
    value = uuid4().hex[:12]
    return f"{prefix}{value}" if prefix else value


def sla_deadline_for_priority(priority: str) -> datetime:
    hours = {"P1": 1, "P2": 4, "P3": 8, "P4": 24}.get(priority, 24)
    return datetime.now(timezone.utc) + timedelta(hours=hours)
