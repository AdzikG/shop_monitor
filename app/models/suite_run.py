from sqlalchemy import String, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
import enum


class SuiteRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"  # wszystkie scenariusze ok
    FAILED = "failed"    # przynajmniej jeden scenariusz failed
    PARTIAL = "partial"  # niektore scenariusze skipped/failed
    CANCELLED = "cancelled"


class SuiteRun(Base):
    """
    Pojedyncze uruchomienie calej suite.
    Agreguje wiele scenario_runs.
    
    Dashboard pokazuje suite_runs, nie pojedyncze scenariusze.
    """
    __tablename__ = "suite_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("suites.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    
    status: Mapped[SuiteRunStatus] = mapped_column(
        Enum(SuiteRunStatus), default=SuiteRunStatus.RUNNING, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual")
    
    # Statystyki
    total_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    success_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    failed_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    total_alerts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relacje
    suite: Mapped["Suite"] = relationship(back_populates="suite_runs")
    environment: Mapped["Environment"] = relationship(back_populates="suite_runs")
    scenario_runs: Mapped[list["ScenarioRun"]] = relationship(
        back_populates="suite_run", cascade="all, delete-orphan"
    )
    alert_groups: Mapped[list["AlertGroup"]] = relationship(
        back_populates="last_suite_run",  # ← POPRAWNE
        foreign_keys="AlertGroup.last_suite_run_id"
    )

    @property
    def duration_seconds(self) -> int | None:
        if self.finished_at and self.started_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    def __repr__(self) -> str:
        return f"<SuiteRun id={self.id} suite={self.suite_id} status={self.status}>"
