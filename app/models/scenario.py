from sqlalchemy import String, Boolean, JSON, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class Scenario(Base):
    """
    Pojedynczy scenariusz do weryfikacji.
    Scenariusz nie nalezy do jednej suite — moze byc w wielu (przez SuiteScenario).
    """
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Konfiguracja scenariusza (odpowiednik kolumn z Google Sheets)
    listing_urls: Mapped[list | None] = mapped_column(JSON)       # lista URL listingow
    delivery_name: Mapped[str | None] = mapped_column(String(255))
    payment_name: Mapped[str | None] = mapped_column(String(255))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    should_order: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_params: Mapped[dict | None] = mapped_column(JSON)       # dodatkowe parametry

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relacje
    suite_scenarios: Mapped[list["SuiteScenario"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="scenario")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="scenario")

    def __repr__(self) -> str:
        return f"<Scenario {self.name}>"
