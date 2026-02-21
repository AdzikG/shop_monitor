from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
import enum


class AlertType(str, enum.Enum):
    BUG = "bug"
    VERIFY = "verify"
    DISABLED = "disabled"
    TEMP_DISABLED = "temp_disabled"


class Alert(Base):
    """
    Alert nałożony podczas uruchomienia scenariusza.

    Kazdy alert wie:
    - ktore uruchomienie (run_id)
    - ktory scenariusz (scenario_id)
    - ktore srodowisko (environment_id) — dzieki temu mozna filtrowac RC vs PROD
    - jaka regula biznesowa go wygenerowala (business_rule)
    - czy jest liczony w raporcie (is_counted) — False dla disabled/temp_disabled
    """
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("scenario_runs.id"), nullable=False)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), nullable=False)

    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    business_rule: Mapped[str] = mapped_column(String(255), nullable=False)
    is_counted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relacje
    run: Mapped["ScenarioRun"] = relationship(back_populates="alerts")
    scenario: Mapped["Scenario"] = relationship(back_populates="alerts")
    environment: Mapped["Environment"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert [{self.alert_type}] {self.business_rule} | {self.title[:50]}>"
