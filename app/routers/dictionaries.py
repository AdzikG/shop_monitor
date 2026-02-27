from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.dictionary import Dictionary
from app.templates import templates

router = APIRouter(tags=["dictionaries"])


@router.get("/dictionaries")
async def dictionaries_list(request: Request, db: Session = Depends(get_db)):
    entries = db.query(Dictionary).order_by(Dictionary.order).all()
    return templates.TemplateResponse("dictionaries/list.html", {
        "request": request,
        "entries": entries,
    })


@router.get("/dictionaries/new")
async def dictionary_new_form(request: Request):
    return templates.TemplateResponse("dictionaries/form.html", {
        "request": request,
        "entry": None,
        "mode": "create",
    })


@router.post("/dictionaries/new")
async def dictionary_create(
    request: Request,
    db: Session = Depends(get_db),
    category: str = Form(...),
    system_name: str = Form(...),
    display_name: str = Form(...),
    description: str = Form(""),
    value: str = Form(""),
    value_type: str = Form("list"),
    order: int = Form(0),
    is_active: bool = Form(False),
):
    entry = Dictionary(
        category=category,
        system_name=system_name,
        display_name=display_name,
        description=description or None,
        value=value or None,
        value_type=value_type,
        order=order,
        is_active=is_active,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(url="/dictionaries", status_code=303)


@router.get("/dictionaries/{entry_id}/edit")
async def dictionary_edit_form(entry_id: int, request: Request, db: Session = Depends(get_db)):
    entry = _get_or_404(db, entry_id)
    return templates.TemplateResponse("dictionaries/form.html", {
        "request": request,
        "entry": entry,
        "mode": "edit",
    })


@router.post("/dictionaries/{entry_id}/edit")
async def dictionary_update(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    category: str = Form(...),
    system_name: str = Form(...),
    display_name: str = Form(...),
    description: str = Form(""),
    value: str = Form(""),
    value_type: str = Form("list"),
    order: int = Form(0),
    is_active: bool = Form(False),
):
    entry = _get_or_404(db, entry_id)
    entry.category = category
    entry.system_name = system_name
    entry.display_name = display_name
    entry.description = description or None
    entry.value = value or None
    entry.value_type = value_type
    entry.order = order
    entry.is_active = is_active
    db.commit()
    return RedirectResponse(url="/dictionaries", status_code=303)


@router.post("/dictionaries/{entry_id}/delete")
async def dictionary_delete(entry_id: int, db: Session = Depends(get_db)):
    entry = _get_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
    return RedirectResponse(url="/dictionaries", status_code=303)


def _get_or_404(db: Session, entry_id: int) -> Dictionary:
    entry = db.query(Dictionary).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Nie znaleziono wpisu")
    return entry
