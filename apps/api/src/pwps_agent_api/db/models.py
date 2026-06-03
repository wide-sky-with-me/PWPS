from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from pwps_agent_api.db.base import Base


class RunRecord(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    raw_input: Mapped[str] = mapped_column(String, nullable=False)
    workflow_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    outputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    trace_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    pending_decision_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
