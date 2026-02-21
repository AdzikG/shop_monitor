from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import json

from database import get_db
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario
from app.models.run import ScenarioRun
from app.templates import templates

router = APIRouter(tags=["scenarios"])


@router.get("/scenarios")
async def scenarios_list(request: Request, db: Session = Depends(get_db)):
    """Lista wszystkich scenariuszy."""
    scenarios = db.query(Scenario).order_by(Scenario.name).all()
    return templates.TemplateResponse("scenarios_list.html", {
        "request": request,
        "scenarios": scenarios,
    })


@router.get("/scenarios/new")
async def scenario_new_form(request: Request):
    """Formularz nowego scenariusza."""
    return templates.TemplateResponse("scenario_form.html", {
        "request": request,
        "scenario": None,
        "mode": "create",
    })


@router.post("/scenarios/new")
async def scenario_create(
    name: str = Form(...),
    description: str = Form(""),
    listing_urls: str = Form(""),
    delivery_name: str = Form(""),
    payment_name: str = Form(""),
    postal_code: str = Form(""),
    should_order: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Utworzenie nowego scenariusza."""
    
    urls = [u.strip() for u in listing_urls.split('\n') if u.strip()]
    
    scenario = Scenario(
        name=name,
        description=description,
        listing_urls=urls,
        delivery_name=delivery_name or None,
        payment_name=payment_name or None,
        postal_code=postal_code or None,
        should_order=should_order,
    )
    
    db.add(scenario)
    db.commit()
    
    return RedirectResponse(url="/scenarios", status_code=303)


@router.get("/scenarios/{scenario_id}")
async def scenario_detail(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    """Szczegoly scenariusza."""
    scenario = db.query(Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    suite_links = db.query(SuiteScenario).filter_by(scenario_id=scenario_id).all()
    
    recent_runs = (
        db.query(ScenarioRun)
        .filter_by(scenario_id=scenario_id)
        .order_by(ScenarioRun.started_at.desc())
        .limit(20)
        .all()
    )
    
    return templates.TemplateResponse("scenario_detail.html", {
        "request": request,
        "scenario": scenario,
        "suite_links": suite_links,
        "recent_runs": recent_runs,
    })


@router.get("/scenarios/{scenario_id}/edit")
async def scenario_edit_form(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    """Formularz edycji scenariusza."""
    scenario = db.query(Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return templates.TemplateResponse("scenario_form.html", {
        "request": request,
        "scenario": scenario,
        "mode": "edit",
    })


@router.post("/scenarios/{scenario_id}/edit")
async def scenario_update(
    scenario_id: int,
    request: Request,  # potrzebne do odczytu form data
    db: Session = Depends(get_db)
):
    """Aktualizacja scenariusza."""
    scenario = db.query(Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Odczyt form data
    form = await request.form()
    
    urls = [u.strip() for u in form.get('listing_urls', '').split('\n') if u.strip()]
    
    scenario.name = form.get('name', '')
    scenario.description = form.get('description', '')
    scenario.listing_urls = urls
    scenario.delivery_name = form.get('delivery_name') or None
    scenario.payment_name = form.get('payment_name') or None
    scenario.postal_code = form.get('postal_code') or None
    scenario.should_order = 'should_order' in form  # checkbox - obecnosc = True
    scenario.is_active = 'is_active' in form  # checkbox - obecnosc = True
    
    db.commit()
    
    return RedirectResponse(url=f"/scenarios/{scenario_id}", status_code=303)


@router.post("/scenarios/{scenario_id}/delete")
async def scenario_delete(scenario_id: int, db: Session = Depends(get_db)):
    """Usuniecie scenariusza."""
    scenario = db.query(Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    db.query(SuiteScenario).filter_by(scenario_id=scenario_id).delete()
    db.delete(scenario)
    db.commit()
    
    return RedirectResponse(url="/scenarios", status_code=303)
