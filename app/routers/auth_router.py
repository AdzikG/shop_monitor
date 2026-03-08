"""
Router autoryzacji — login/logout/setup.
"""

import re
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

USERNAME_RE = re.compile(r'^[a-z]+_[a-z]+$')

from database import get_db
from app.models.user import User
from app.templates import templates
from core.auth_core import (
    verify_password, hash_password, create_session, end_session,
    SESSION_COOKIE, COOKIE_MAX_AGE, get_current_user
)

router = APIRouter(tags=["auth"])


@router.get("/auth/login")
async def login_form(request: Request, db: Session = Depends(get_db)):
    # Jeśli brak użytkowników → setup
    if db.query(User).count() == 0:
        return RedirectResponse("/auth/setup", status_code=303)
    # Już zalogowany → dashboard
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    next_url = request.query_params.get("next", "/")
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "next_url": next_url,
        "error": None,
    })


@router.post("/auth/login")
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
):
    user = db.query(User).filter_by(username=username, is_active=True).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "next_url": next_url,
            "error": "Nieprawidłowy login lub hasło",
        }, status_code=401)

    token = create_session(user)
    response = RedirectResponse(next_url if next_url.startswith("/") else "/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/auth/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        end_session(token)
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/auth/setup")
async def setup_form(request: Request, db: Session = Depends(get_db)):
    # Dostępne tylko gdy brak użytkowników
    if db.query(User).count() > 0:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse("auth/setup.html", {
        "request": request,
        "error": None,
    })


@router.post("/auth/setup")
async def setup_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    if db.query(User).count() > 0:
        return RedirectResponse("/auth/login", status_code=303)

    if not USERNAME_RE.match(username.strip()):
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": "Nieprawidłowy format loginu — wymagany: imie_nazwisko (tylko małe litery)",
        }, status_code=400)

    if password != password2:
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": "Hasła nie są identyczne",
        }, status_code=400)

    if len(password) < 4:
        return templates.TemplateResponse("auth/setup.html", {
            "request": request,
            "error": "Hasło musi mieć co najmniej 4 znaki",
        }, status_code=400)

    admin = User(
        username=username.strip(),
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()

    token = create_session(admin)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response
