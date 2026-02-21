from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Time, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from datetime import time, date


class AlertConfig(Base):
    """
    Konfiguracja alertu - definiuje kiedy i jak alert ma byc wyswietlany.
    
    Tylko alerty z konfiguracja beda wyswietlane.
    """
    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Identyfikacja
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_rule: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    # Typ alertu
    alert_type_id: Mapped[int] = mapped_column(ForeignKey("alert_types.id"), nullable=False)
    
    # Opis
    description: Mapped[str | None] = mapped_column(Text)
    
    # Harmonogram wylaczen (opcjonalny)
    disabled_from_date: Mapped[date | None] = mapped_column(Date)
    disabled_to_date: Mapped[date | None] = mapped_column(Date)
    disabled_from_time: Mapped[time | None] = mapped_column(Time)
    disabled_to_time: Mapped[time | None] = mapped_column(Time)
    
    # On/Off
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Metadane
    updated_by: Mapped[str | None] = mapped_column(String(100))
    
    # Relacje
    alert_type: Mapped["AlertType"] = relationship(back_populates="alert_configs")

    def is_disabled_now(self) -> bool:
        """Sprawdza czy alert jest wylaczony w tym momencie (harmonogram)."""
        if not self.is_active:
            return True
        
        from datetime import datetime
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        
        # Sprawdz zakres dat
        if self.disabled_from_date and self.disabled_to_date:
            if not (self.disabled_from_date <= today <= self.disabled_to_date):
                return False
        
        # Sprawdz zakres godzin
        if self.disabled_from_time and self.disabled_to_time:
            if not (self.disabled_from_time <= current_time <= self.disabled_to_time):
                return False
        
        # Jesli mamy zakres dat/godzin i jestesmy w nim - wylaczony
        if self.disabled_from_date or self.disabled_from_time:
            return True
        
        return False

    def __repr__(self) -> str:
        return f"<AlertConfig {self.business_rule} [{self.alert_type.slug if self.alert_type else 'N/A'}]>"
