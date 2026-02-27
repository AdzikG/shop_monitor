from sqlalchemy import String, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class Scenario(Base):
    """
    Scenariusz testowy — konfiguracja pojedynczego testu e-commerce.
    """
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Podstawowe
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # URLe listingu (JSON array)
    listing_urls: Mapped[list] = mapped_column(JSON, default=list)

    # Dostawa
    delivery_name: Mapped[str | None] = mapped_column(String(255))
    delivery_cutoff: Mapped[str | None] = mapped_column(String(10))  # np. "15:00"

    # Płatność
    payment_name: Mapped[str | None] = mapped_column(String(255))

    # Koszyk
    basket_type: Mapped[str | None] = mapped_column(String(100))
    services: Mapped[str | None] = mapped_column(Text)   # JSON array stringów np. '["montaz"]'

    # Adres
    postal_code: Mapped[str | None] = mapped_column(String(20))

    # Opcje
    is_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guarantee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relacje
    suite_scenarios: Mapped[list["SuiteScenario"]] = relationship(
        back_populates="scenario"
    )
    runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="scenario")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="scenario")
    flags: Mapped[list["ScenarioFlag"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )

    def get_services(self) -> list[str]:
        """Zwraca listę usług."""
        if not self.services:
            return []
        import json
        try:
            return json.loads(self.services)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_flags_dict(self) -> dict[str, bool]:
        """Zwraca słownik flag {name: is_enabled} dla Playwright."""
        return {sf.flag.name: sf.is_enabled for sf in self.flags}

    def __repr__(self) -> str:
        return f"<Scenario {self.name}>"
