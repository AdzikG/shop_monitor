from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AlertType(Base):
    """
    Typy alertow (blad, do poprawy, etc.).
    Osobna tabela pozwala na dodawanie nowych typow bez zmiany kodu.
    """
    __tablename__ = "alert_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # bug, to_verify, etc.
    color: Mapped[str | None] = mapped_column(String(20))  # hex color dla UI
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relacje
    alert_configs: Mapped[list["AlertConfig"]] = relationship(back_populates="alert_type")

    def __repr__(self) -> str:
        return f"<AlertType {self.slug}>"
