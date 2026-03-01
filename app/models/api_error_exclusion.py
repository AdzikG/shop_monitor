from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, now_utc
from datetime import datetime


class ApiErrorExclusion(Base):
    __tablename__ = "api_error_exclusions"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_pattern: Mapped[str] = mapped_column(String(1000), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
