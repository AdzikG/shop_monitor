from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class ScheduledJob(Base):
    """
    Zaplanowane uruchomienie suite — kombinacja suite + environment + cron.
    Scheduler sprawdza co minutę które joby są do uruchomienia.
    """
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Konfiguracja uruchomienia
    suite_id: Mapped[int] = mapped_column(ForeignKey("suites.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)
    workers: Mapped[int] = mapped_column(Integer, default=2)

    # Harmonogram
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    # Przykłady:
    # "0 8 * * 1-5"   — o 8:00 w dni robocze
    # "0 * * * *"     — co godzinę
    # "*/30 * * * *"  — co 30 minut
    # "0 9,15 * * *"  — o 9:00 i 15:00 każdego dnia

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tracking
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_suite_run_id: Mapped[int | None] = mapped_column(ForeignKey("suite_runs.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relacje
    suite: Mapped["Suite"] = relationship(back_populates="scheduled_jobs")
    environment: Mapped["Environment"] = relationship(back_populates="scheduled_jobs")
    last_suite_run: Mapped["SuiteRun | None"] = relationship(foreign_keys=[last_suite_run_id])

    def __repr__(self) -> str:
        return f"<ScheduledJob suite={self.suite_id} env={self.environment_id} cron='{self.cron}'>"
