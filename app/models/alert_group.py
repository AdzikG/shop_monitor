from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
import enum


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class AlertGroup(Base):
    """
    Grupuje ten sam alert wystepujacy w wielu scenariuszach w obrebie jednego suite run.
    
    Przyklad:
        Suite run #123 odpala 50 scenariuszy.
        15 z nich generuje alert "calendar.day_unavailable".
        
        Zamiast 15 osobnych alertow w zakładce Alerts:
        → 1 AlertGroup z lista 15 scenario_ids
    
    Pozwala na weryfikacje/zamykanie grupowo.
    """
    __tablename__ = "alert_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_run_id: Mapped[int] = mapped_column(ForeignKey("suite_runs.id"), nullable=False)
    
    # Identyfikacja alertu
    business_rule: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bug/verify/disabled
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Workflow
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus), default=AlertStatus.OPEN, nullable=False
    )
    
    # Agregacja
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0)  # ile razy wystapil
    scenario_ids: Mapped[str] = mapped_column(Text)  # JSON lista scenario_ids: "[1,5,12,...]"
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Notatki weryfikacyjne
    notes: Mapped[str | None] = mapped_column(Text)
    closed_by: Mapped[str | None] = mapped_column(String(100))
    
    # Relacje
    suite_run: Mapped["SuiteRun"] = relationship(back_populates="alert_groups")

    def __repr__(self) -> str:
        return f"<AlertGroup {self.business_rule} x{self.occurrence_count} [{self.status}]>"
