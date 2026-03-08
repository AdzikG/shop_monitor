from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import ScenarioRun
    from app.models.alert import Alert
    from app.models.suite_run import SuiteRun
    from app.models.scheduled_job import ScheduledJob


class Environment(Base):
    """
    Srodowisko testowe — PRE, RC, PROD.
    Przechowuje URL sklepu i typ srodowiska.
    """
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=now_utc)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relacje
    runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="environment")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="environment")

    def __repr__(self) -> str:
        return f"<Environment {self.name} — {self.base_url}>"

    suite_runs: Mapped[list["SuiteRun"]] = relationship(back_populates="environment")
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(back_populates="environment", cascade="all, delete-orphan")
