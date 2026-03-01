from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
import html
from pathlib import Path
from datetime import datetime, timezone

from database import get_db
from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.models.run import ScenarioRun, RunStatus
from app.models.alert import Alert
from app.models.basket_snapshot import BasketSnapshot
from app.models.api_error import ApiError
from app.templates import templates
from core import runner_registry

router = APIRouter(tags=["suite_runs"])

PAGE_SIZE = 25


@router.get("/suite-runs")
async def suite_runs_list(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
):
    total = db.query(SuiteRun).count()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE

    runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .offset(offset)
        .limit(PAGE_SIZE)
        .all()
    )

    # Które suite_run_id są aktualnie uruchomione
    running_ids = set(runner_registry.get_running().keys())

    return templates.TemplateResponse("suite_runs_list.html", {
        "request": request,
        "runs": runs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "page_size": PAGE_SIZE,
        "running_ids": running_ids,
    })


@router.get("/suite-runs/{suite_run_id}")
async def suite_run_detail(suite_run_id: int, request: Request, db: Session = Depends(get_db)):
    suite_run = db.query(SuiteRun).filter(SuiteRun.id == suite_run_id).first()
    if not suite_run:
        raise HTTPException(status_code=404, detail="Suite run not found")

    scenario_runs = (
        db.query(ScenarioRun)
        .filter(ScenarioRun.suite_run_id == suite_run_id)
        .order_by(ScenarioRun.started_at)
        .all()
    )

    alert_groups = []
    for group in suite_run.alert_groups:
        try:
            scenario_ids = json.loads(group.scenario_ids) if group.scenario_ids else []
        except Exception:
            scenario_ids = []

        alert_groups.append({
            'id': group.id,
            'business_rule': group.business_rule,
            'title': group.title,
            'alert_type': group.alert_type,
            'occurrence_count': group.occurrence_count,
            'scenario_ids': scenario_ids,
        })

    is_running = runner_registry.is_running(suite_run_id)

    return templates.TemplateResponse("suite_run_detail.html", {
        "request": request,
        "suite_run": suite_run,
        "scenario_runs": scenario_runs,
        "alert_groups": alert_groups,
        "is_running": is_running,
    })


@router.get("/suite-runs/{suite_run_id}/{id}")
async def scenario_run_detail(
    suite_run_id: int,
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    suite_run = db.query(SuiteRun).filter(SuiteRun.id == suite_run_id).first()
    if not suite_run:
        raise HTTPException(status_code=404, detail="Suite run not found")

    run = db.query(ScenarioRun).filter(
        ScenarioRun.suite_run_id == suite_run_id,
        ScenarioRun.id == id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    alerts = db.query(Alert).filter(Alert.run_id == run.id).all()
    snapshots = db.query(BasketSnapshot).filter(BasketSnapshot.run_id == run.id).all()
    api_errors = db.query(ApiError).filter(ApiError.run_id == run.id).all()

    return templates.TemplateResponse("suite_run_scenario_detail.html", {
        "request": request,
        "suite_run": suite_run,
        "run": run,
        "alerts": alerts,
        "snapshots": snapshots,
        "api_errors": api_errors,
    })


@router.post("/suite-runs/{suite_run_id}/cancel")
async def cancel_suite_run(suite_run_id: int, db: Session = Depends(get_db)):
    """Anuluje trwający suite run."""

    suite_run = db.query(SuiteRun).filter(SuiteRun.id == suite_run_id).first()
    if not suite_run:
        raise HTTPException(status_code=404, detail="Suite run not found")

    if not runner_registry.is_running(suite_run_id):
        raise HTTPException(status_code=400, detail="Suite run nie jest aktualnie uruchomiony")

    cancelled = runner_registry.cancel(suite_run_id)

    if cancelled:
        # Status zostanie ustawiony przez _run_suite_background po CancelledError
        # Ale na wszelki wypadek ustawiamy też tutaj
        suite_run.status = SuiteRunStatus.CANCELLED
        suite_run.finished_at = datetime.now(timezone.utc)
        scenario_runs = (
                db.query(ScenarioRun)
                .filter(ScenarioRun.suite_run_id == suite_run_id)
                .order_by(ScenarioRun.started_at)
                .all()
            )
        for scenario in scenario_runs:
            scenario.status = RunStatus.CANCELLED
            scenario.finished_at = datetime.now(timezone.utc)
        db.commit()

    return JSONResponse({"ok": cancelled, "suite_run_id": suite_run_id})


@router.get("/suite-runs/{suite_run_id}/logs", response_class=HTMLResponse)
async def suite_run_logs(suite_run_id: int):
    log_file = Path(f"logs/suite_run_{suite_run_id}.log")

    if not log_file.exists():
        return "<div style='padding: 2rem; text-align: center; color: var(--text-secondary);'>Brak logów</div>"

    try:
        content = log_file.read_text(encoding='utf-8')
        escaped = html.escape(content)
        return f"""<pre style='margin:0; padding:1rem; background:var(--bg-dark); color:var(--text-primary);
                    font-size:11px; line-height:1.6; overflow-x:auto;
                    font-family:"Fira Code",monospace;
                    white-space:pre-wrap; word-wrap:break-word;'>{escaped}</pre>"""
    except Exception as e:
        return f"<div style='padding:2rem; color:var(--accent-red);'>Błąd ładowania logów: {e}</div>"
