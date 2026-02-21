"""
Alert Engine — zbiera alerty z scenariuszy i zapisuje do bazy.

ZASADA: TYLKO alerty z konfiguracja (alert_configs) sa wyswietlane.
Jesli alert nie ma konfiguracji — zostanie ZIGNOROWANY.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.alert_config import AlertConfig
from app.models.alert_type import AlertType

logger = logging.getLogger(__name__)


class AlertEngine:
    """Zbiera alerty podczas wykonywania scenariusza."""

    def __init__(self, run_id: int, scenario_id: int, environment_id: int, db: Session):
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.environment_id = environment_id
        self.db = db
        self.alerts = []

    def add_alert(self, rule: str, description: str | None = None):
        """
        Dodaje alert TYLKO jesli ma konfiguracje i jest aktywny.
        
        Args:
            rule: business_rule (np. "cart.add_to_cart_failed")
            description: opcjonalny szczegolowy opis (np. treść błędu)
        """
        
        # Sprawdz czy istnieje konfiguracja dla tego alertu
        config = self.db.query(AlertConfig).filter_by(business_rule=rule).first()
        
        if not config:
            logger.debug(f"Alert '{rule}' nie ma konfiguracji — IGNORUJE")
            return
        
        # Sprawdz czy alert jest aktywny
        if not config.is_active:
            logger.debug(f"Alert '{rule}' wylaczony (is_active=False) — IGNORUJE")
            return
        
        # Sprawdz harmonogram
        if config.is_disabled_now():
            logger.debug(f"Alert '{rule}' wylaczony harmonogramem — IGNORUJE")
            return
        
        # Pobierz typ alertu i title z konfiguracji
        alert_type = config.alert_type
        title = config.name  # nazwa z konfiguracji jako title
        
        # Utworz alert
        alert = Alert(
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            environment_id=self.environment_id,
            business_rule=rule,
            alert_type=alert_type.slug,
            title=title,
            description=description,
            is_counted=True,
        )
        
        self.alerts.append(alert)
        logger.info(f"Alert dodany: {rule} [{alert_type.name}]")

    def counted_alerts(self) -> int:
        """Liczba alertow liczonych (wszystkie skonfigurowane sa liczone)."""
        return len(self.alerts)

    def save_all(self):
        """Zapisuje wszystkie alerty do bazy."""
        if not self.alerts:
            logger.debug("Brak alertow do zapisania")
            return
        
        self.db.add_all(self.alerts)
        self.db.flush()
        
        logger.info(f"Zapisano {len(self.alerts)} alertow")