from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    """Zwraca aktualny czas UTC z informacją o timezone."""
    return datetime.now(timezone.utc)


# SQLite nie wspiera timezone-aware datetime natywnie
# Ten event listener dodaje UTC timezone do wszystkich datetime przy odczycie
@event.listens_for(Base, "load", propagate=True)
def receive_load(target, context):
    """Automatycznie dodaje UTC timezone do datetime przy odczycie z SQLite."""
    for key in target.__mapper__.columns.keys():
        value = getattr(target, key, None)
        if isinstance(value, datetime) and value.tzinfo is None:
            # Datetime bez timezone — załóż że to UTC (bo tak zapisujemy)
            setattr(target, key, value.replace(tzinfo=timezone.utc))