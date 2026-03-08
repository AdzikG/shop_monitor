"""
System autoryzacji oparty na kontach użytkowników.
Sesje przechowywane w pamięci — giną po restarcie serwera.
"""

import secrets
import bcrypt
from fastapi import Request
from typing import Optional

SESSION_COOKIE = "sm_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 godzin

# In-memory sessions: {token: {user_id, username, role}}
active_sessions: dict[str, dict] = {}


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_session(user) -> str:
    """Tworzy sesję dla użytkownika, zwraca token."""
    token = secrets.token_hex(32)
    active_sessions[token] = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }
    return token


def end_session(token: str) -> None:
    active_sessions.pop(token, None)


def get_session(token: Optional[str]) -> Optional[dict]:
    """Zwraca dane sesji lub None."""
    if not token:
        return None
    return active_sessions.get(token)


def get_current_user(request: Request) -> Optional[dict]:
    """Pobiera aktualnego użytkownika z ciasteczka. Zwraca dict lub None."""
    token = request.cookies.get(SESSION_COOKIE)
    return get_session(token)


def require_auth(request: Request) -> dict:
    """Dependency — 401 jeśli brak sesji."""
    from fastapi import HTTPException
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Wymagane logowanie")
    return user


def require_admin(request: Request) -> dict:
    """Dependency — 403 jeśli nie admin."""
    from fastapi import HTTPException
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Wymagane logowanie")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Wymagane uprawnienia admina")
    return user
