from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc

from database import get_db
from app.models.suite import Suite
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario
from app.templates import templates

router = APIRouter(tags=["suites"])


# ─────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────

@router.get("/suites")
async def suites_list(request: Request, db: Session = Depends(get_db)):
    suites = (
        db.query(Suite)
        .order_by(Suite.id)
        .all()
    )
    # Dołącz liczbę scenariuszy do każdej suite
    for suite in suites:
        suite._all_scenario_count = (
            db.query(SuiteScenario)
            .filter_by(suite_id=suite.id, is_active=True)
            .count()
        )
        suite._active_scenario_count = (
            db.query(SuiteScenario)
            .join(Scenario, SuiteScenario.scenario_id == Scenario.id)
            .filter(
                SuiteScenario.suite_id == suite.id,
                SuiteScenario.is_active == True,
                Scenario.is_active == True,
            )
            .count()
        )
    return templates.TemplateResponse("suites/list.html", {
        "request": request,
        "suites": suites,
    })


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────

@router.get("/suites/new")
async def suite_new_form(request: Request, db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).filter_by(is_active=True).order_by(Scenario.name).all()
    return templates.TemplateResponse("suites/form.html", {
        "request": request,
        "suite": None,
        "scenarios": scenarios,
        "assigned_ids": [],
        "title": "Nowa Suite",
    })


@router.post("/suites/new")
async def suite_create(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(""),
    workers: int = Form(2),
    is_active: bool = Form(False),
    scenario_ids: list[int] = Form(default=[]),
):
    suite = Suite(
        name=name,
        description=description or None,
        workers=workers,
        is_active=is_active,
    )
    db.add(suite)
    db.flush()  # pobierz suite.id przed commitem

    _sync_suite_scenarios(db, suite.id, scenario_ids)

    db.commit()
    return RedirectResponse(url=f"/suites/{suite.id}", status_code=303)


# ─────────────────────────────────────────────
# DETAIL
# ─────────────────────────────────────────────

@router.get("/suites/{suite_id}")
async def suite_detail(suite_id: int, request: Request, db: Session = Depends(get_db)):
    suite = _get_or_404(db, suite_id)
    suite_scenarios = (
        db.query(SuiteScenario)
        .join(Scenario, SuiteScenario.scenario_id == Scenario.id)
        .filter(
            SuiteScenario.suite_id == suite_id,
            SuiteScenario.is_active == True,
            Scenario.is_active == True,
        )
        .order_by(SuiteScenario.order)
        .all()
    )
    return templates.TemplateResponse("suites/detail.html", {
        "request": request,
        "suite": suite,
        "suite_scenarios": suite_scenarios,
    })


# ─────────────────────────────────────────────
# EDIT
# ─────────────────────────────────────────────

@router.get("/suites/{suite_id}/edit")
async def suite_edit_form(suite_id: int, request: Request, db: Session = Depends(get_db)):
    suite = _get_or_404(db, suite_id)
    scenarios = db.query(Scenario).order_by(Scenario.name).all()
    assigned_ids = [
        ss.scenario_id
        for ss in db.query(SuiteScenario)
        .filter_by(suite_id=suite_id, is_active=True)
        .order_by(SuiteScenario.order)
        .all()
    ]
    return templates.TemplateResponse("suites/form.html", {
        "request": request,
        "suite": suite,
        "scenarios": scenarios,
        "assigned_ids": assigned_ids,
        "title": f"Edycja: {suite.name}",
    })


@router.post("/suites/{suite_id}/edit")
async def suite_update(
    suite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(""),
    workers: int = Form(2),
    is_active: bool = Form(False),
    scenario_ids: list[int] = Form(default=[]),
):
    suite = _get_or_404(db, suite_id)
    suite.name = name
    suite.description = description or None
    suite.workers = workers
    suite.is_active = is_active

    _sync_suite_scenarios(db, suite_id, scenario_ids)

    db.commit()
    return RedirectResponse(url=f"/suites/{suite_id}", status_code=303)


# ─────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────

@router.post("/suites/{suite_id}/delete")
async def suite_delete(suite_id: int, db: Session = Depends(get_db)):
    suite = _get_or_404(db, suite_id)
    # Soft delete — deactivate zamiast usuwania
    suite.is_active = False
    db.query(SuiteScenario).filter_by(suite_id=suite_id).update({"is_active": False})
    db.commit()
    return RedirectResponse(url="/suites", status_code=303)


# ─────────────────────────────────────────────
# HTMX — reorder scenarios (drag&drop kolejność)
# ─────────────────────────────────────────────

@router.post("/suites/{suite_id}/reorder")
async def suite_reorder(
    suite_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Przyjmuje JSON body: {"scenario_ids": [3, 1, 2]} i ustawia order."""
    body = await request.json()
    ordered_ids = body.get("scenario_ids", [])

    for index, scenario_id in enumerate(ordered_ids):
        db.query(SuiteScenario).filter_by(
            suite_id=suite_id, scenario_id=scenario_id
        ).update({"order": index})

    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_or_404(db: Session, suite_id: int) -> Suite:
    suite = db.query(Suite).filter(Suite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite nie znaleziona")
    return suite


def _sync_suite_scenarios(db: Session, suite_id: int, scenario_ids: list[int]):
    """
    Synchronizuje SuiteScenario dla danej suite.
    - Usuwa (deaktywuje) stare wpisy których nie ma w nowej liście
    - Dodaje nowe wpisy
    - Zachowuje kolejność z listy scenario_ids
    """
    existing = {
        ss.scenario_id: ss
        for ss in db.query(SuiteScenario).filter_by(suite_id=suite_id).all()
    }

    new_set = set(scenario_ids)

    # Deaktywuj usuniętych
    for sid, ss in existing.items():
        if sid not in new_set:
            ss.is_active = False

    # Dodaj lub reaktywuj
    for order, sid in enumerate(scenario_ids):
        if sid in existing:
            ss = existing[sid]
            ss.is_active = True
            ss.order = order
        else:
            db.add(SuiteScenario(suite_id=suite_id, scenario_id=sid, order=order, is_active=True))
