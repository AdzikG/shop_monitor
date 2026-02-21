from sqlalchemy import String, DateTime, ForeignKey, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime
from decimal import Decimal


class BasketSnapshot(Base):
    """
    Stan koszyka na danym etapie uruchomienia.
    Jeden run ma wiele snapshotow — po jednym na etap koszyka.

    Etapy: list / transport / payment / address / summary / thank_you
    """
    __tablename__ = "basket_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("scenario_runs.id"), nullable=False)

    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    product_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    delivery_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    raw_data: Mapped[dict | None] = mapped_column(JSON)  # pelne dane koszyka na tym etapie
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relacje
    run: Mapped["ScenarioRun"] = relationship(back_populates="basket_snapshots")

    def __repr__(self) -> str:
        return f"<BasketSnapshot run={self.run_id} stage={self.stage}>"
