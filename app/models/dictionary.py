from sqlalchemy import String, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, now_utc
from datetime import datetime


class Dictionary(Base):
    """
    Słownik wartości dla list wyboru w scenariuszach.
    Jedna encja = jedna kategoria z listą wartości.
    Przykład: category="delivery", value="Kurier DPD, InPost, Paczkomat"
    """
    __tablename__ = "dictionaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    system_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(20), default="list", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    def get_values(self) -> list[str]:
        """Zwraca listę wartości z pola value (CSV)."""
        if not self.value:
            return []
        return [v.strip() for v in self.value.split(",") if v.strip()]

    def __repr__(self) -> str:
        return f"<Dictionary {self.category}:{self.system_name}>"
