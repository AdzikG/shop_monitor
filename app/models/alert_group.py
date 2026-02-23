from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from datetime import datetime, timezone

from app.models.base import Base, now_utc


class AlertStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class AlertGroup(Base):
    """
    Grupa alertów — deduplikacja alertów z tego samego business_rule.
    Jeśli alert powtarza się w kolejnych runach, zwiększa się repeat_count.
    """
    __tablename__ = "alert_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Ostatni suite_run który zaktualizował ten alert
    last_suite_run_id: Mapped[int] = mapped_column(ForeignKey("suite_runs.id"), nullable=False)
    
    # Historia wszystkich suite_run_ids które ten alert wygenerowały
    suite_run_history: Mapped[list] = mapped_column(JSON, default=list)
    
    # Business rule
    business_rule: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Typ alertu (slug z alert_types)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Title z alert_config (snapshot, NIE computed)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Ile razy wystąpił w OSTATNIM suite_run
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # IDs scenariuszy z OSTATNIEGO suite_run (JSON list)
    scenario_ids: Mapped[str] = mapped_column(Text, nullable=False)
    
    # ILE RAZY POWTÓRZYŁ SIĘ (główna nowa funkcjonalność)
    repeat_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Status workflow
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, native_enum=False, length=20),
        default=AlertStatus.OPEN,
        nullable=False
    )
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Workflow metadata
    notes: Mapped[str | None] = mapped_column(Text)
    closed_by: Mapped[str | None] = mapped_column(String(100))
    
    # Relacje
    last_suite_run: Mapped["SuiteRun"] = relationship(back_populates="alert_groups")

    def __repr__(self) -> str:
        return f"<AlertGroup {self.business_rule} [repeat: {self.repeat_count}x]>"
