from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class SuiteEnvironment(Base):
    """
    Relacja wiele-do-wielu: Suite <-> Environment.

    Jeden wiersz = jedna konfiguracja uruchomien:
    ta sama suite moze miec rozny cron i workers na roznych srodowiskach.

    Przyklad:
        Suite "Bez zamowien" na RC   → cron co godzine,  workers=4
        Suite "Bez zamowien" na PROD → cron co 6 godzin, workers=6
    """
    __tablename__ = "suite_environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("suites.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)

    cron_expression: Mapped[str | None] = mapped_column(String(100))
    workers_override: Mapped[int | None] = mapped_column(Integer)  # nadpisuje workers z Suite
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relacje
    suite: Mapped["Suite"] = relationship(back_populates="suite_environments")
    environment: Mapped["Environment"] = relationship(back_populates="suite_environments")

    @property
    def effective_workers(self) -> int:
        """Zwraca workers — override jesli ustawiony, inaczej z Suite."""
        return self.workers_override or self.suite.workers

    def __repr__(self) -> str:
        return f"<SuiteEnvironment suite={self.suite_id} env={self.environment_id}>"
