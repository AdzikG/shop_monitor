from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.environment import Environment
from app.templates import templates

router = APIRouter(tags=["environments"])


@router.get("/environments")
async def environments_list(request: Request, db: Session = Depends(get_db)):
    envs = db.query(Environment).order_by(Environment.name, Environment.id).all()
    return templates.TemplateResponse("environments/list.html", {
        "request": request,
        "envs": envs,
    })


@router.get("/environments/new")
async def environment_new_form(request: Request):
    return templates.TemplateResponse("environments/form.html", {
        "request": request,
        "env": None,
        "mode": "create",
    })


@router.post("/environments/new")
async def environment_create(
    db: Session = Depends(get_db),
    name: str = Form(...),
    base_url: str = Form(...),
    type: str = Form(""),
    is_active: bool = Form(False),
):
    env = Environment(
        name=name,
        base_url=base_url,
        type=type,
        is_active=is_active,
    )
    db.add(env)
    db.commit()
    return RedirectResponse(url="/environments", status_code=303)


@router.get("/environments/{env_id}/edit")
async def environment_edit_form(env_id: int, request: Request, db: Session = Depends(get_db)):
    env = _get_or_404(db, env_id)
    return templates.TemplateResponse("environments/form.html", {
        "request": request,
        "env": env,
        "mode": "edit",
    })


@router.post("/environments/{env_id}/edit")
async def environment_update(
    env_id: int,
    db: Session = Depends(get_db),
    name: str = Form(...),
    base_url: str = Form(...),
    type: str = Form(""),
    is_active: bool = Form(False),
):
    env = _get_or_404(db, env_id)
    env.name = name
    env.base_url = base_url
    env.type = type
    env.is_active = is_active
    db.commit()
    return RedirectResponse(url="/environments", status_code=303)


@router.post("/environments/{env_id}/delete")
async def environment_delete(env_id: int, db: Session = Depends(get_db)):
    env = _get_or_404(db, env_id)
    db.delete(env)
    db.commit()
    return RedirectResponse(url="/environments", status_code=303)


def _get_or_404(db: Session, env_id: int) -> Environment:
    env = db.query(Environment).filter_by(id=env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Nie znaleziono środowiska")
    return env
