from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, now_utc
from datetime import datetime


class ApiError(Base):
    """
    Blad API przechwycony podczas uruchomienia scenariusza.
    Zapisuje wszystkie odpowiedzi HTTP powyzej 400.
    """
    __tablename__ = "api_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("scenario_runs.id"), nullable=False)

    endpoint: Mapped[str] = mapped_column(String(1000), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)   # GET/POST/PUT/DELETE
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)  # np. 404, 500
    response_body: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relacje
    run: Mapped["ScenarioRun"] = relationship(back_populates="api_errors")

    def __repr__(self) -> str:
        return f"<ApiError {self.method} {self.status_code} {self.endpoint[:50]}>"
