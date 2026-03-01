from sqlalchemy import String, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class Environment(Base):
    """
    Srodowisko testowe — PRE, RC, PROD.
    Przechowuje URL sklepu i dane logowania per srodowisko.
    """
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    login: Mapped[str | None] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255))
    extra_config: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relacje
    runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="environment")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="environment")

    def __repr__(self) -> str:
        return f"<Environment {self.name} — {self.base_url}>"

    suite_runs: Mapped[list["SuiteRun"]] = relationship(back_populates="environment")
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(back_populates="environment", cascade="all, delete-orphan")
