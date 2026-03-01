from sqlalchemy import String, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class Suite(Base):
    """
    Grupa scenariuszy — np. "Z zamowieniami", "Top 1000", "Bez zamowien".
    Suite nie jest przywiazana do srodowiska — moze dzialac na wielu.
    """
    __tablename__ = "suites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    workers: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relacje
    suite_scenarios: Mapped[list["SuiteScenario"]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )
    runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="suite")

    def __repr__(self) -> str:
        return f"<Suite {self.name} workers={self.workers}>"

    suite_runs: Mapped[list["SuiteRun"]] = relationship(back_populates="suite")
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(back_populates="suite", cascade="all, delete-orphan")
