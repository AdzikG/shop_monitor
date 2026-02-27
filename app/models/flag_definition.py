from sqlalchemy import String, Boolean, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class FlagDefinition(Base):
    """
    Globalna definicja flagi zachowania testu.
    Flagi są przypisywane do scenariuszy przez ScenarioFlag.
    """
    __tablename__ = "flag_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relacje
    scenario_flags: Mapped[list["ScenarioFlag"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FlagDefinition {self.name}>"


class ScenarioFlag(Base):
    """
    Przypisanie flagi do scenariusza (many-to-many z atrybutem is_enabled).
    """
    __tablename__ = "scenario_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    flag_id: Mapped[int] = mapped_column(ForeignKey("flag_definitions.id", ondelete="CASCADE"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacje
    scenario: Mapped["Scenario"] = relationship(back_populates="flags")
    flag: Mapped["FlagDefinition"] = relationship(back_populates="scenario_flags")

    def __repr__(self) -> str:
        return f"<ScenarioFlag scenario={self.scenario_id} flag={self.flag_id} enabled={self.is_enabled}>"
