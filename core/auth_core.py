"""
Prosta autoryzacja PIN dla panelu Shop Monitor.
Chroni wszystkie POST/DELETE endpointy.
Token sesyjny trzymany w pamięci — ginie po restarcie serwera.
"""

import os
import secrets
from fastapi import HTTPException, Cookie, status
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# PIN z .env
PANEL_PIN: str = os.getenv("PANEL_PIN")
if not PANEL_PIN:
    raise RuntimeError("PANEL_PIN nie jest ustawiony w .env")

# Aktywne tokeny sesyjne — in-memory
active_tokens: set[str] = set()

SESSION_COOKIE = "sm_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 godzin


def generate_token() -> str:
    return secrets.token_hex(32)


def verify_pin(pin: str) -> Optional[str]:
    """Sprawdza PIN, zwraca token sesji lub None."""
    if secrets.compare_digest(pin.strip(), PANEL_PIN):
        token = generate_token()
        active_tokens.add(token)
        return token
    return None


def check_session(sm_session: Optional[str] = Cookie(None)) -> bool:
    """Dependency — sprawdza czy sesja jest aktywna."""
    return sm_session is not None and sm_session in active_tokens


def require_session(sm_session: Optional[str] = Cookie(None)):
    """Dependency dla POST/DELETE — rzuca 403 jeśli brak sesji."""
    if sm_session is None or sm_session not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wymagana autoryzacja PIN"
        )
