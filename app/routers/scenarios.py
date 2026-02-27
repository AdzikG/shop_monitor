from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import json

from database import get_db
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario
from app.models.run import ScenarioRun
from app.models.dictionary import Dictionary
from app.models.flag_definition import FlagDefinition, ScenarioFlag
from app.templates import templates

router = APIRouter(tags=["scenarios"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_form_context(db: Session) -> dict:
    def get_values(system_name: str) -> list[str]:
        entry = db.query(Dictionary).filter_by(system_name=system_name, is_active=True).first()
        return entry.get_values() if entry else []

    return {
        "deliveries":   get_values("available_deliveries"),
        "payments":     get_values("available_payments"),
        "basket_types": get_values("basket_types"),
        "services":     get_values("available_services"),
        "all_flags":    db.query(FlagDefinition).filter_by(is_active=True).order_by(FlagDefinition.display_name).all(),
    }


def _get_or_404(db: Session, scenario_id: int) -> Scenario:
    scenario = db.query(Scenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenariusz nie znaleziony")
    return scenario


def _save_flags(db: Session, scenario_id: int, enabled_flag_ids: list[int], all_flags: list):
    db.query(ScenarioFlag).filter_by(scenario_id=scenario_id).delete()
    for flag in all_flags:
        db.add(ScenarioFlag(
            scenario_id=scenario_id,
            flag_id=flag.id,
            is_enabled=flag.id in enabled_flag_ids,
        ))


# ── LIST ─────────────────────────────────────────────────────────────────────

@router.get("/scenarios")
async def scenarios_list(request: Request, db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).order_by(Scenario.name).all()
    ctx = _get_form_context(db)

    scenario_flags_map = {
        s.id: {sf.flag_id: sf.is_enabled for sf in s.flags}
        for s in scenarios
    }

    return templates.TemplateResponse("scenarios_list.html", {
        "request": request,
        "scenarios": scenarios,
        "scenario_flags_map": scenario_flags_map,
        **ctx,
    })


# ── INLINE ────────────────────────────────────────────────────────────────────

@router.post("/scenarios/inline-create")
async def scenario_inline_create(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nazwa jest wymagana")
    scenario = Scenario(name=name, listing_urls=[], is_active=False)
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return JSONResponse({"ok": True, "id": scenario.id})


@router.post("/scenarios/{scenario_id}/inline")
async def scenario_inline_update(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    scenario = _get_or_404(db, scenario_id)
    body = await request.json()
    field = body.get("field")
    value = body.get("value")

    allowed = {"name", "delivery_name", "payment_name", "basket_type",
               "postal_code", "is_active", "is_order", "guarantee", "delivery_cutoff"}
    if field not in allowed:
        raise HTTPException(status_code=400, detail=f"Pole '{field}' niedozwolone")

    if field in ("is_active", "is_order", "guarantee"):
        setattr(scenario, field, bool(value))
    else:
        setattr(scenario, field, value or None)

    db.commit()
    return JSONResponse({"ok": True})


@router.post("/scenarios/{scenario_id}/inline-flags")
async def scenario_inline_flags(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    _get_or_404(db, scenario_id)
    body = await request.json()
    flag_id = int(body.get("flag_id"))
    is_enabled = bool(body.get("is_enabled"))

    sf = db.query(ScenarioFlag).filter_by(scenario_id=scenario_id, flag_id=flag_id).first()
    if sf:
        sf.is_enabled = is_enabled
    else:
        db.add(ScenarioFlag(scenario_id=scenario_id, flag_id=flag_id, is_enabled=is_enabled))
    db.commit()
    return JSONResponse({"ok": True})


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.get("/scenarios/new")
async def scenario_new_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("scenario_form.html", {
        "request": request,
        "scenario": None,
        "mode": "create",
        "enabled_flag_ids": [],
        **_get_form_context(db),
    })


@router.post("/scenarios/new")
async def scenario_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    urls = [u.strip() for u in form.get("listing_urls", "").split("\n") if u.strip()]
    selected_services = form.getlist("services")

    scenario = Scenario(
        name=form.get("name", ""),
        description=form.get("description") or None,
        listing_urls=urls,
        delivery_name=form.get("delivery_name") or None,
        delivery_cutoff=form.get("delivery_cutoff") or None,
        payment_name=form.get("payment_name") or None,
        basket_type=form.get("basket_type") or None,
        services=json.dumps(selected_services) if selected_services else None,
        postal_code=form.get("postal_code") or None,
        is_order="is_order" in form,
        guarantee="guarantee" in form,
        is_active=True,
    )
    db.add(scenario)
    db.flush()

    all_flags = db.query(FlagDefinition).filter_by(is_active=True).all()
    enabled_ids = [int(i) for i in form.getlist("flag_ids")]
    _save_flags(db, scenario.id, enabled_ids, all_flags)

    db.commit()
    return RedirectResponse(url=f"/scenarios/{scenario.id}", status_code=303)


# ── DETAIL ────────────────────────────────────────────────────────────────────

@router.get("/scenarios/{scenario_id}")
async def scenario_detail(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    scenario = _get_or_404(db, scenario_id)
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


# ── EDIT ──────────────────────────────────────────────────────────────────────

@router.get("/scenarios/{scenario_id}/edit")
async def scenario_edit_form(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    scenario = _get_or_404(db, scenario_id)
    enabled_flag_ids = [sf.flag_id for sf in scenario.flags if sf.is_enabled]
    return templates.TemplateResponse("scenario_form.html", {
        "request": request,
        "scenario": scenario,
        "mode": "edit",
        "enabled_flag_ids": enabled_flag_ids,
        **_get_form_context(db),
    })


@router.post("/scenarios/{scenario_id}/edit")
async def scenario_update(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    scenario = _get_or_404(db, scenario_id)
    form = await request.form()
    urls = [u.strip() for u in form.get("listing_urls", "").split("\n") if u.strip()]
    selected_services = form.getlist("services")

    scenario.name = form.get("name", "")
    scenario.description = form.get("description") or None
    scenario.listing_urls = urls
    scenario.delivery_name = form.get("delivery_name") or None
    scenario.delivery_cutoff = form.get("delivery_cutoff") or None
    scenario.payment_name = form.get("payment_name") or None
    scenario.basket_type = form.get("basket_type") or None
    scenario.services = json.dumps(selected_services) if selected_services else None
    scenario.postal_code = form.get("postal_code") or None
    scenario.is_order = "is_order" in form
    scenario.guarantee = "guarantee" in form
    scenario.is_active = "is_active" in form

    all_flags = db.query(FlagDefinition).filter_by(is_active=True).all()
    enabled_ids = [int(i) for i in form.getlist("flag_ids")]
    _save_flags(db, scenario.id, enabled_ids, all_flags)

    db.commit()
    return RedirectResponse(url=f"/scenarios/{scenario_id}", status_code=303)


# ── COPY ──────────────────────────────────────────────────────────────────────

@router.post("/scenarios/{scenario_id}/copy")
async def scenario_copy(scenario_id: int, db: Session = Depends(get_db)):
    original = _get_or_404(db, scenario_id)
    copy = Scenario(
        name=f"{original.name} (kopia)",
        description=original.description,
        listing_urls=original.listing_urls,
        delivery_name=original.delivery_name,
        delivery_cutoff=original.delivery_cutoff,
        payment_name=original.payment_name,
        basket_type=original.basket_type,
        services=original.services,
        postal_code=original.postal_code,
        is_order=original.is_order,
        guarantee=original.guarantee,
        is_active=False,
    )
    db.add(copy)
    db.flush()
    for sf in original.flags:
        db.add(ScenarioFlag(scenario_id=copy.id, flag_id=sf.flag_id, is_enabled=sf.is_enabled))
    db.commit()
    return RedirectResponse(url=f"/scenarios/{copy.id}/edit", status_code=303)


# ── DELETE ────────────────────────────────────────────────────────────────────

@router.post("/scenarios/{scenario_id}/delete")
async def scenario_delete(scenario_id: int, db: Session = Depends(get_db)):
    scenario = _get_or_404(db, scenario_id)
    db.query(SuiteScenario).filter_by(scenario_id=scenario_id).delete()
    db.delete(scenario)
    db.commit()
    return RedirectResponse(url="/scenarios", status_code=303)
