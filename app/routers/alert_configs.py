from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, time

from database import get_db
from app.models.alert_config import AlertConfig
from app.models.alert_type import AlertType
from app.templates import templates

router = APIRouter(tags=["alert_configs"])


@router.get("/alert-configs")
async def alert_configs_list(request: Request, db: Session = Depends(get_db)):
    """Lista konfiguracji alertow."""
    configs = db.query(AlertConfig).order_by(AlertConfig.name).all()
    return templates.TemplateResponse("alert_configs_list.html", {
        "request": request,
        "configs": configs,
    })


@router.get("/alert-configs/new")
async def alert_config_new_form(request: Request, db: Session = Depends(get_db)):
    """Formularz nowej konfiguracji."""
    alert_types = db.query(AlertType).filter_by(is_active=True).all()
    return templates.TemplateResponse("alert_config_form.html", {
        "request": request,
        "config": None,
        "alert_types": alert_types,
        "mode": "create",
    })


@router.post("/alert-configs/new")
async def alert_config_create(
    request: Request,
    db: Session = Depends(get_db)
):
    """Utworzenie nowej konfiguracji."""
    form = await request.form()
    
    # Parse date/time (opcjonalne)
    disabled_from_date = form.get('disabled_from_date')
    disabled_to_date = form.get('disabled_to_date')
    disabled_from_time = form.get('disabled_from_time')
    disabled_to_time = form.get('disabled_to_time')
    
    config = AlertConfig(
        name=form.get('name'),
        business_rule=form.get('business_rule'),
        alert_type_id=int(form.get('alert_type_id')),
        description=form.get('description') or None,
        disabled_from_date=date.fromisoformat(disabled_from_date) if disabled_from_date else None,
        disabled_to_date=date.fromisoformat(disabled_to_date) if disabled_to_date else None,
        disabled_from_time=time.fromisoformat(disabled_from_time) if disabled_from_time else None,
        disabled_to_time=time.fromisoformat(disabled_to_time) if disabled_to_time else None,
        is_active='is_active' in form,
        updated_by=form.get('updated_by') or None,
    )
    
    db.add(config)
    db.commit()
    
    return RedirectResponse(url="/alert-configs", status_code=303)


@router.get("/alert-configs/{config_id}")
async def alert_config_detail(config_id: int, request: Request, db: Session = Depends(get_db)):
    """Szczegoly konfiguracji."""
    config = db.query(AlertConfig).filter_by(id=config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return templates.TemplateResponse("alert_config_detail.html", {
        "request": request,
        "config": config,
    })


@router.get("/alert-configs/{config_id}/edit")
async def alert_config_edit_form(config_id: int, request: Request, db: Session = Depends(get_db)):
    """Formularz edycji."""
    config = db.query(AlertConfig).filter_by(id=config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    alert_types = db.query(AlertType).filter_by(is_active=True).all()
    return templates.TemplateResponse("alert_config_form.html", {
        "request": request,
        "config": config,
        "alert_types": alert_types,
        "mode": "edit",
    })


@router.post("/alert-configs/{config_id}/edit")
async def alert_config_update(
    config_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Aktualizacja konfiguracji."""
    config = db.query(AlertConfig).filter_by(id=config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    form = await request.form()
    
    disabled_from_date = form.get('disabled_from_date')
    disabled_to_date = form.get('disabled_to_date')
    disabled_from_time = form.get('disabled_from_time')
    disabled_to_time = form.get('disabled_to_time')
    
    config.name = form.get('name')
    config.business_rule = form.get('business_rule')
    config.alert_type_id = int(form.get('alert_type_id'))
    config.description = form.get('description') or None
    config.disabled_from_date = date.fromisoformat(disabled_from_date) if disabled_from_date else None
    config.disabled_to_date = date.fromisoformat(disabled_to_date) if disabled_to_date else None
    config.disabled_from_time = time.fromisoformat(disabled_from_time) if disabled_from_time else None
    config.disabled_to_time = time.fromisoformat(disabled_to_time) if disabled_from_time else None
    config.is_active = 'is_active' in form
    config.updated_by = form.get('updated_by') or None
    
    db.commit()
    
    return RedirectResponse(url=f"/alert-configs/{config_id}", status_code=303)


@router.post("/alert-configs/{config_id}/delete")
async def alert_config_delete(config_id: int, db: Session = Depends(get_db)):
    """Usuniecie konfiguracji."""
    config = db.query(AlertConfig).filter_by(id=config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    db.delete(config)
    db.commit()
    
    return RedirectResponse(url="/alert-configs", status_code=303)
