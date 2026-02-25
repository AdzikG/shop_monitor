from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
import json
from datetime import datetime, timezone
from typing import Optional

from database import get_db
from app.models.alert_group import (
    AlertGroup, AlertStatus, ResolutionType, RESOLUTION_TO_STATUS
)
from app.models.suite_run import SuiteRun
from app.models.environment import Environment
from app.models.scenario import Scenario
from app.templates import templates

router = APIRouter(tags=["alerts"])


# ── Lista alertów ─────────────────────────────────────────────────────────────

@router.get("/alerts")
async def alerts_list(
    request: Request,
    status: str = "active",
    environment_id: str = "all",
    search: str = "",
    db: Session = Depends(get_db)
):
    query = (
        db.query(AlertGroup)
        .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
        .order_by(desc(AlertGroup.last_seen_at))
    )

    # Filtr statusu
    if status == "active":
        query = query.filter(AlertGroup.status.in_([
            AlertStatus.OPEN,
            AlertStatus.IN_PROGRESS,
        ]))
    elif status == "awaiting":
        query = query.filter(AlertGroup.status.in_([
            AlertStatus.AWAITING_FIX,
            AlertStatus.AWAITING_TEST_UPDATE,
        ]))
    elif status == "closed":
        query = query.filter(AlertGroup.status == AlertStatus.CLOSED)
    # "all" — bez filtra

    # Filtr środowiska
    if environment_id != "all":
        query = query.filter(SuiteRun.environment_id == int(environment_id))

    # Wyszukiwanie
    if search:
        query = query.filter(
            or_(
                AlertGroup.business_rule.ilike(f"%{search}%"),
                AlertGroup.title.ilike(f"%{search}%")
            )
        )

    alert_groups = query.limit(200).all()

    # Statystyki
    total_open = db.query(AlertGroup).filter(
        AlertGroup.status.in_([AlertStatus.OPEN, AlertStatus.IN_PROGRESS])
    ).count()
    total_awaiting = db.query(AlertGroup).filter(
        AlertGroup.status.in_([AlertStatus.AWAITING_FIX, AlertStatus.AWAITING_TEST_UPDATE])
    ).count()
    total_closed = db.query(AlertGroup).filter(
        AlertGroup.status == AlertStatus.CLOSED
    ).count()

    # Backlog — AWAITING_FIX + AWAITING_TEST_UPDATE (dla sekcji na dole)
    backlog = (
        db.query(AlertGroup)
        .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
        .filter(AlertGroup.status.in_([
            AlertStatus.AWAITING_FIX,
            AlertStatus.AWAITING_TEST_UPDATE,
        ]))
        .order_by(desc(AlertGroup.repeat_count))
        .all()
    ) if status in ("active", "awaiting", "all") else []

    environments = db.query(Environment).filter_by(is_active=True).all()

    # Załaduj scenariusze dla wyświetlenia nazw
    all_scenario_ids = set()
    for ag in alert_groups + backlog:
        try:
            ids = json.loads(ag.scenario_ids)
            all_scenario_ids.update(ids)
        except (json.JSONDecodeError, TypeError):
            pass

    scenarios_map = {}
    if all_scenario_ids:
        scenarios = db.query(Scenario).filter(Scenario.id.in_(all_scenario_ids)).all()
        scenarios_map = {s.id: s for s in scenarios}

    return templates.TemplateResponse("alerts_list.html", {
        "request": request,
        "alert_groups": alert_groups,
        "backlog": backlog,
        "current_status": status,
        "current_environment": environment_id,
        "search_query": search,
        "total_open": total_open,
        "total_awaiting": total_awaiting,
        "total_closed": total_closed,
        "environments": environments,
        "scenarios_map": scenarios_map,
        "resolution_types": [r.value for r in ResolutionType],
    })


# ── Szczegóły alertu ──────────────────────────────────────────────────────────

@router.get("/alerts/{alert_group_id}")
async def alert_detail(
    alert_group_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    alert = db.query(AlertGroup).filter(AlertGroup.id == alert_group_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    # Historia runów — szczegóły każdego
    try:
        run_ids = json.loads(alert.suite_run_history) if alert.suite_run_history else []
    except (json.JSONDecodeError, TypeError):
        run_ids = []

    suite_runs = []
    if run_ids:
        suite_runs = (
            db.query(SuiteRun)
            .filter(SuiteRun.id.in_(run_ids))
            .order_by(desc(SuiteRun.started_at))
            .all()
        )

    # Parent (jeśli duplikat)
    parent = None
    if alert.duplicate_of_id:
        parent = db.query(AlertGroup).get(alert.duplicate_of_id)

    # Scenariusze
    try:
        scenario_ids = json.loads(alert.scenario_ids)
    except (json.JSONDecodeError, TypeError):
        scenario_ids = []

    scenarios = db.query(Scenario).filter(Scenario.id.in_(scenario_ids)).all() if scenario_ids else []

    return templates.TemplateResponse("alert_detail.html", {
        "request": request,
        "alert": alert,
        "suite_runs": suite_runs,
        "parent": parent,
        "scenarios": scenarios,
        "resolution_types": [r.value for r in ResolutionType],
    })


# ── Assign — start weryfikacji ────────────────────────────────────────────────

@router.post("/alerts/{alert_group_id}/assign")
async def assign_alert(
    alert_group_id: int,
    analyst_name: str = Form(...),
    db: Session = Depends(get_db)
):
    alert = db.query(AlertGroup).filter(AlertGroup.id == alert_group_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    alert.assigned_to  = analyst_name
    alert.assigned_at  = datetime.now(timezone.utc)

    if alert.status == AlertStatus.OPEN:
        alert.status = AlertStatus.IN_PROGRESS

    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


# ── Resolve — zamknięcie z resolution ────────────────────────────────────────

@router.post("/alerts/{alert_group_id}/resolve")
async def resolve_alert(
    alert_group_id: int,
    resolution_type: str = Form(...),
    resolution_note: str = Form(""),
    duplicate_of_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    alert = db.query(AlertGroup).filter(AlertGroup.id == alert_group_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    try:
        res_type = ResolutionType(resolution_type)
    except ValueError:
        return RedirectResponse(url="/alerts", status_code=303)

    # Wyznacz nowy status na podstawie resolution_type
    new_status = RESOLUTION_TO_STATUS[res_type]

    # Konwertuj duplicate_of_id — pusty string z formularza traktuj jako None
    dup_id: Optional[int] = None
    if duplicate_of_id and duplicate_of_id.strip():
        try:
            dup_id = int(duplicate_of_id.strip())
        except ValueError:
            pass

    alert.resolution_type = res_type.value
    alert.resolution_note = resolution_note or None
    alert.status          = new_status
    alert.resolved_at     = datetime.now(timezone.utc)

    if res_type == ResolutionType.DUPLICATE and dup_id:
        alert.duplicate_of_id = dup_id

    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


# ── Legacy — zmiana statusu (wsteczna kompatybilność) ────────────────────────

@router.post("/alerts/{alert_group_id}/status")
async def update_alert_status(
    alert_group_id: int,
    new_status: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    alert = db.query(AlertGroup).filter(AlertGroup.id == alert_group_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    try:
        alert.status = AlertStatus(new_status)
    except ValueError:
        return RedirectResponse(url="/alerts", status_code=303)

    if notes:
        alert.notes = notes

    if new_status == "closed":
        alert.closed_at = datetime.now(timezone.utc)

    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)