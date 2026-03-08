from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.flag_definition import FlagDefinition
from app.templates import templates
from core.auth_core import get_current_user

router = APIRouter(tags=["flags"])


@router.get("/flags")
async def flags_list(request: Request, db: Session = Depends(get_db)):
    flags = db.query(FlagDefinition).order_by(FlagDefinition.name).all()
    return templates.TemplateResponse("flags/list.html", {
        "request": request,
        "flags": flags,
    })


@router.get("/flags/new")
async def flag_new_form(request: Request):
    return templates.TemplateResponse("flags/form.html", {
        "request": request,
        "flag": None,
        "mode": "create",
    })


@router.post("/flags/new")
async def flag_create(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    display_name: str = Form(...),
    description: str = Form(""),
    is_active: bool = Form(False),
):
    user = get_current_user(request)
    username = user["username"] if user else None
    flag = FlagDefinition(
        name=name,
        display_name=display_name,
        description=description or None,
        is_active=is_active,
        created_by=username,
        updated_by=username,
    )
    db.add(flag)
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)


@router.get("/flags/{flag_id}/edit")
async def flag_edit_form(flag_id: int, request: Request, db: Session = Depends(get_db)):
    flag = _get_or_404(db, flag_id)
    return templates.TemplateResponse("flags/form.html", {
        "request": request,
        "flag": flag,
        "mode": "edit",
    })


@router.post("/flags/{flag_id}/edit")
async def flag_update(
    flag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    display_name: str = Form(...),
    description: str = Form(""),
    is_active: bool = Form(False),
):
    flag = _get_or_404(db, flag_id)
    user = get_current_user(request)
    flag.name = name
    flag.display_name = display_name
    flag.description = description or None
    flag.is_active = is_active
    flag.updated_by = user["username"] if user else None
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)


@router.post("/flags/{flag_id}/delete")
async def flag_delete(flag_id: int, db: Session = Depends(get_db)):
    flag = _get_or_404(db, flag_id)
    db.delete(flag)
    db.commit()
    return RedirectResponse(url="/flags", status_code=303)


def _get_or_404(db: Session, flag_id: int) -> FlagDefinition:
    flag = db.query(FlagDefinition).filter_by(id=flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Nie znaleziono flagi")
    return flag
