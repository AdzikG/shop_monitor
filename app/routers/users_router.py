"""
CRUD użytkowników — dostępne tylko dla adminów.
"""

import re
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

USERNAME_RE = re.compile(r'^[a-z]+_[a-z]+$')

from database import get_db
from app.models.user import User
from app.templates import templates
from core.auth_core import require_admin, hash_password

router = APIRouter(tags=["users"])


@router.get("/users")
async def users_list(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse("users/list.html", {
        "request": request,
        "users": users,
    })


@router.get("/users/new")
async def user_new_form(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse("users/form.html", {
        "request": request,
        "user": None,
        "mode": "create",
        "error": None,
    })


@router.post("/users/new")
async def user_create(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(False),
):
    if not USERNAME_RE.match(username.strip()):
        return templates.TemplateResponse("users/form.html", {
            "request": request,
            "user": None,
            "mode": "create",
            "error": "Nieprawidłowy format loginu — wymagany: imie_nazwisko (tylko małe litery)",
        }, status_code=400)

    if db.query(User).filter_by(username=username).first():
        return templates.TemplateResponse("users/form.html", {
            "request": request,
            "user": None,
            "mode": "create",
            "error": f"Użytkownik '{username}' już istnieje",
        }, status_code=400)

    user = User(
        username=username.strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/users", status_code=303)


@router.get("/users/{user_id}/edit")
async def user_edit_form(user_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = _get_or_404(db, user_id)
    return templates.TemplateResponse("users/form.html", {
        "request": request,
        "user": user,
        "mode": "edit",
        "error": None,
    })


@router.post("/users/{user_id}/edit")
async def user_update(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
    username: str = Form(...),
    password: str = Form(""),
    role: str = Form("user"),
    is_active: bool = Form(False),
):
    user = _get_or_404(db, user_id)
    if not USERNAME_RE.match(username.strip()):
        return templates.TemplateResponse("users/form.html", {
            "request": request,
            "user": user,
            "mode": "edit",
            "error": "Nieprawidłowy format loginu — wymagany: imie_nazwisko (tylko małe litery)",
        }, status_code=400)

    # Sprawdź unikalność username (pomijając siebie)
    existing = db.query(User).filter(User.username == username, User.id != user_id).first()
    if existing:
        return templates.TemplateResponse("users/form.html", {
            "request": request,
            "user": user,
            "mode": "edit",
            "error": f"Użytkownik '{username}' już istnieje",
        }, status_code=400)

    user.username = username.strip()
    user.role = role
    user.is_active = is_active
    if password.strip():
        user.password_hash = hash_password(password)

    db.commit()
    return RedirectResponse("/users", status_code=303)


@router.post("/users/{user_id}/delete")
async def user_delete(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = _get_or_404(db, user_id)
    # Nie można usunąć ostatniego aktywnego admina
    if user.role == "admin" and user.is_active:
        active_admins = db.query(User).filter_by(role="admin", is_active=True).count()
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Nie można usunąć ostatniego aktywnego admina")
    db.delete(user)
    db.commit()
    return RedirectResponse("/users", status_code=303)


def _get_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    return user
