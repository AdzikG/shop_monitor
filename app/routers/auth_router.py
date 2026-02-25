"""
Router autoryzacji — endpoint weryfikacji PINu.
"""

from fastapi import APIRouter, Form, Cookie
from fastapi.responses import JSONResponse, Response
from typing import Optional

from core.auth_core import verify_pin, active_tokens, SESSION_COOKIE, COOKIE_MAX_AGE

router = APIRouter(tags=["auth"])


@router.post("/auth/verify-pin")
async def verify_pin_endpoint(
    pin: str = Form(...),
    sm_session: Optional[str] = Cookie(None)
):
    """
    Weryfikuje PIN i ustawia cookie sesyjne.
    Zwraca JSON — obsługiwany przez JavaScript w modalu.
    """
    # Już zalogowany
    if sm_session and sm_session in active_tokens:
        return JSONResponse({"ok": True})

    token = verify_pin(pin)
    if not token:
        return JSONResponse({"ok": False, "error": "Nieprawidłowy PIN"}, status_code=401)

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax"
    )
    return response


@router.post("/auth/logout")
async def logout(response: Response):
    """Usuwa cookie sesyjne."""
    response.delete_cookie(SESSION_COOKIE)
    return JSONResponse({"ok": True})


@router.get("/auth/check-session")
async def check_session(sm_session: Optional[str] = Cookie(None)):
    """Sprawdza czy sesja jest aktywna — używane przez JS przed każdą akcją POST."""
    ok = sm_session is not None and sm_session in active_tokens
    return JSONResponse({"ok": ok})
