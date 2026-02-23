from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone

templates = Jinja2Templates(directory="app/templates")

# Custom filter dla Jinja2
def duration(seconds):
    """Konwertuje sekundy na czytelny format."""
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

def local_time(dt):
    """Konwertuje UTC datetime na lokalny czas."""
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        # Jesli brak timezone, zaloz ze UTC
        dt = dt.replace(tzinfo=timezone.utc)
    # Konwertuj na lokalny czas
    local_dt = dt.astimezone()
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')

# Rejestracja filtrow
templates.env.filters["duration"] = duration
templates.env.filters["local_time"] = local_time

def parse_json(value):
    """Parsuje JSON string do Python object."""
    import json
    try:
        return json.loads(value) if value else []
    except:
        return []

templates.env.filters["parse_json"] = parse_json
