from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
import enum


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScenarioRun(Base):
    """
    Jedno uruchomienie pojedynczego scenariusza.
    Teraz nalezy do suite_run (agregacja).
    """
    __tablename__ = "scenario_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_run_id: Mapped[int] = mapped_column(ForeignKey("suite_runs.id"), nullable=False)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    suite_id: Mapped[int] = mapped_column(ForeignKey("suites.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)

    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), default=RunStatus.RUNNING, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Wyniki
    product_id: Mapped[str | None] = mapped_column(String(255))
    product_name: Mapped[str | None] = mapped_column(String(500))
    screenshot_url: Mapped[str | None] = mapped_column(String(1000))
    video_url: Mapped[str | None] = mapped_column(String(1000))

    # Relacje
    suite_run: Mapped["SuiteRun"] = relationship(back_populates="scenario_runs")
    scenario: Mapped["Scenario"] = relationship(back_populates="runs")
    suite: Mapped["Suite"] = relationship(back_populates="runs")
    environment: Mapped["Environment"] = relationship(back_populates="runs")
    basket_snapshots: Mapped[list["BasketSnapshot"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    api_errors: Mapped[list["ApiError"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    @property
    def duration_seconds(self) -> int | None:
        if self.finished_at and self.started_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    def __repr__(self) -> str:
        return f"<ScenarioRun id={self.id} scenario={self.scenario_id} status={self.status}>"
