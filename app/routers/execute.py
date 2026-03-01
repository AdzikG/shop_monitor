from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
import asyncio
from database import SessionLocal, get_db
from app.models.suite import Suite
from app.models.environment import Environment
from app.models.suite_scenario import SuiteScenario
from app.models.scenario import Scenario
from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.models.run import ScenarioRun, RunStatus
from scenarios.suite_executor import SuiteExecutor
from app.templates import templates
from core import runner_registry

router = APIRouter(tags=["execute"])

MANUAL_SUITE_NAME = "Manual Runs"


def get_or_create_manual_suite(db: Session) -> Suite:
    suite = db.query(Suite).filter_by(name=MANUAL_SUITE_NAME).first()
    if not suite:
        suite = Suite(
            name=MANUAL_SUITE_NAME,
            description="Ręczne uruchomienia pojedynczych scenariuszy",
            workers=2,
            is_active=True,
        )
        db.add(suite)
        db.commit()
        db.refresh(suite)
    return suite


@router.get("/execute")
async def execute_form(request: Request, db: Session = Depends(get_db)):
    suites = db.query(Suite).filter(
        Suite.is_active == True,
        Suite.name != MANUAL_SUITE_NAME
    ).all()
    environments = db.query(Environment).filter(Environment.is_active == True).all()
    scenarios = db.query(Scenario).filter(Scenario.is_active == True).order_by(Scenario.id).all()

    running_count = runner_registry.count_running()

    return templates.TemplateResponse("execute_form.html", {
        "request": request,
        "suites": suites,
        "environments": environments,
        "scenarios": scenarios,
        "running_count": running_count,
        "max_concurrent": runner_registry.MAX_CONCURRENT_SUITES,
    })


@router.post("/execute")
async def execute_run(
    request: Request,
    suite_id: int = Form(...),
    environment_id: int = Form(...),
    workers_override: str = Form(""),
    headless: bool = Form(False),
    db: Session = Depends(get_db),
):
    workers = int(workers_override) if workers_override.strip() else None

    # Sprawdź limit przed startem
    if runner_registry.count_running() >= runner_registry.MAX_CONCURRENT_SUITES:
        return templates.TemplateResponse("execute_form.html", {
            "request": request,
            "error": f"Osiągnięto limit {runner_registry.MAX_CONCURRENT_SUITES} równoległych suite.",
            "suites": db.query(Suite).filter(Suite.is_active == True, Suite.name != MANUAL_SUITE_NAME).all(),
            "environments": db.query(Environment).filter(Environment.is_active == True).all(),
            "scenarios": db.query(Scenario).filter(Scenario.is_active == True).all(),
            "running_count": runner_registry.count_running(),
            "max_concurrent": runner_registry.MAX_CONCURRENT_SUITES,
        })

    suite_run_id = await _start_suite(suite_id, environment_id, workers, headless)
    return RedirectResponse(url=f"/suite-runs/{suite_run_id}", status_code=303)


@router.post("/execute/manual")
async def execute_manual(
    scenario_ids: List[int] = Form(...),
    environment_id: int = Form(...),
    headless: bool = Form(False),
):
    suite_run_id = await _start_manual(scenario_ids, environment_id, headless)
    return RedirectResponse(url=f"/suite-runs/{suite_run_id}", status_code=303)


# ── Start helpers ─────────────────────────────────────────────────────────────

async def _start_suite(
    suite_id: int,
    environment_id: int,
    workers_override,
    headless: bool,
    triggered_by: str = "manual",
) -> int:
    """
    Tworzy suite_run w bazie, rejestruje task i zwraca suite_run_id.
    Używane przez execute endpoint i scheduler.
    """
    db = SessionLocal()
    try:
        suite = db.query(Suite).filter_by(id=suite_id).first()
        environment = db.query(Environment).filter_by(id=environment_id).first()

        if not suite or not environment:
            raise HTTPException(status_code=404, detail="Suite lub environment nie znaleziony")

        suite_scenarios = (
            db.query(SuiteScenario)
            .filter_by(suite_id=suite.id, is_active=True)
            .order_by(SuiteScenario.order)
            .all()
        )
        scenarios = [ss.scenario for ss in suite_scenarios if ss.scenario.is_active]

        if not scenarios:
            raise HTTPException(status_code=400, detail="Brak aktywnych scenariuszy w suite")

        workers = workers_override or suite.workers

        # Utwórz suite_run wcześniej żeby mieć ID do registry
        suite_run = SuiteRun(
            suite_id=suite.id,
            environment_id=environment.id,
            status=SuiteRunStatus.RUNNING,
            total_scenarios=len(scenarios),
            triggered_by=triggered_by,
        )
        db.add(suite_run)
        db.commit()
        db.refresh(suite_run)
        suite_run_id = suite_run.id

    finally:
        db.close()

    # Uruchom w tle przez registry
    await runner_registry.run_suite(
        suite_run_id,
        _run_suite_background(suite_run_id, suite_id, environment_id, workers, headless),
    )

    return suite_run_id


async def _start_manual(
    scenario_ids: list,
    environment_id: int,
    headless: bool,
) -> int:
    db = SessionLocal()
    try:
        environment = db.query(Environment).filter_by(id=environment_id).first()
        if not environment:
            raise HTTPException(status_code=404, detail="Environment nie znaleziony")

        scenarios = (
            db.query(Scenario)
            .filter(Scenario.id.in_(scenario_ids), Scenario.is_active == True)
            .all()
        )
        if not scenarios:
            raise HTTPException(status_code=400, detail="Brak aktywnych scenariuszy")

        manual_suite = get_or_create_manual_suite(db)

        suite_run = SuiteRun(
            suite_id=manual_suite.id,
            environment_id=environment.id,
            status=SuiteRunStatus.RUNNING,
            total_scenarios=len(scenarios),
            triggered_by="manual",
        )
        db.add(suite_run)
        db.commit()
        db.refresh(suite_run)
        suite_run_id = suite_run.id

    finally:
        db.close()

    await runner_registry.run_suite(
        suite_run_id,
        _run_manual_background(suite_run_id, scenario_ids, environment_id, headless),
    )

    return suite_run_id


# ── Background coroutines ─────────────────────────────────────────────────────

async def _run_suite_background(
    suite_run_id: int,
    suite_id: int,
    environment_id: int,
    workers: int,
    headless: bool,
):
    db = SessionLocal()
    try:
        suite = db.query(Suite).filter_by(id=suite_id).first()
        environment = db.query(Environment).filter_by(id=environment_id).first()
        suite_run = db.query(SuiteRun).filter_by(id=suite_run_id).first()

        suite_scenarios = (
            db.query(SuiteScenario)
            .filter_by(suite_id=suite.id, is_active=True)
            .order_by(SuiteScenario.order)
            .all()
        )
        scenarios = [ss.scenario for ss in suite_scenarios if ss.scenario.is_active]

        executor = SuiteExecutor(
            suite=suite,
            environment=environment,
            scenarios=scenarios,
            workers=workers,
            headless=headless,
            db=db,
            suite_run=suite_run,  # przekaż istniejący suite_run
        )
        await executor.run()

    except asyncio.CancelledError:
        # Oznacz jako CANCELLED w bazie
        try:
            db2 = SessionLocal()
            suite_run = db2.query(SuiteRun).filter_by(id=suite_run_id).first()
            if suite_run:
                suite_run.status = SuiteRunStatus.CANCELLED
                from datetime import datetime, timezone
                suite_run.finished_at = datetime.now(timezone.utc)
                db2.commit()
            
            scenario_runs = (
                db2.query(ScenarioRun)
                .filter(ScenarioRun.suite_run_id == suite_run_id)
                .order_by(ScenarioRun.started_at)
                .all()
            )
            if scenario_runs:
                for scenario in scenario_runs:
                    scenario.status = RunStatus.CANCELLED
                    from datetime import datetime, timezone
                    scenario.finished_at = datetime.now(timezone.utc)
                db2.commit()
            db2.close()
        except Exception:
            pass
        raise

    finally:
        db.close()


async def _run_manual_background(
    suite_run_id: int,
    scenario_ids: list,
    environment_id: int,
    headless: bool,
):
    db = SessionLocal()
    try:
        environment = db.query(Environment).filter_by(id=environment_id).first()
        scenarios = (
            db.query(Scenario)
            .filter(Scenario.id.in_(scenario_ids), Scenario.is_active == True)
            .all()
        )
        manual_suite = get_or_create_manual_suite(db)
        suite_run = db.query(SuiteRun).filter_by(id=suite_run_id).first()

        executor = SuiteExecutor(
            suite=manual_suite,
            environment=environment,
            scenarios=scenarios,
            workers=len(scenarios),
            headless=headless,
            db=db,
            suite_run=suite_run,
        )
        await executor.run()

    except asyncio.CancelledError:
        try:
            db2 = SessionLocal()
            suite_run = db2.query(SuiteRun).filter_by(id=suite_run_id).first()
            if suite_run:
                suite_run.status = SuiteRunStatus.CANCELLED
                from datetime import datetime, timezone
                suite_run.finished_at = datetime.now(timezone.utc)
                db2.commit()

            scenario_runs = (
                db2.query(ScenarioRun)
                .filter(ScenarioRun.suite_run_id == suite_run_id)
                .order_by(ScenarioRun.started_at)
                .all()
            )
            if scenario_runs:
                for scenario in scenario_runs:
                    scenario.status = RunStatus.CANCELLED
                    from datetime import datetime, timezone
                    scenario.finished_at = datetime.now(timezone.utc)
                db2.commit()
            db2.close()
        except Exception:
            pass
        raise

    finally:
        db.close()
