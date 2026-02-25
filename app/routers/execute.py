from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncio
import threading
import sys
from typing import List

from database import SessionLocal, get_db
from app.models.suite import Suite
from app.models.environment import Environment
from app.models.suite_scenario import SuiteScenario
from app.models.scenario import Scenario
from app.models.suite_run import SuiteRun
from scenarios.suite_executor import SuiteExecutor
from app.templates import templates

router = APIRouter(tags=["execute"])

# Nazwa dedykowanej suite dla manual runs
MANUAL_SUITE_NAME = "Manual Runs"


def get_or_create_manual_suite(db: Session) -> Suite:
    """Zwraca suite 'Manual Runs' — tworzy jeśli nie istnieje."""
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
    """Formularz wyboru suite/scenariuszy i environment do uruchomienia."""
    suites = db.query(Suite).filter(
        Suite.is_active == True,
        Suite.name != MANUAL_SUITE_NAME
    ).all()
    environments = db.query(Environment).filter(Environment.is_active == True).all()
    scenarios = db.query(Scenario).filter(Scenario.is_active == True).order_by(Scenario.id).all()

    return templates.TemplateResponse("execute_form.html", {
        "request": request,
        "suites": suites,
        "environments": environments,
        "scenarios": scenarios,
    })


@router.post("/execute")
async def execute_run(
    suite_id: int = Form(...),
    environment_id: int = Form(...),
    workers_override: str = Form(""),
    headless: bool = Form(False),
):
    """Uruchamia suite w tle."""
    workers = None
    if workers_override and workers_override.strip():
        workers = int(workers_override)

    thread = threading.Thread(
        target=run_suite_in_thread,
        args=(suite_id, environment_id, workers, headless),
        daemon=True
    )
    thread.start()

    return RedirectResponse(url="/suite-runs", status_code=303)


@router.post("/execute/manual")
async def execute_manual(
    scenario_ids: List[int] = Form(...),
    environment_id: int = Form(...),
    headless: bool = Form(False),
):
    """Uruchamia wybrane scenariusze jako manual run."""
    thread = threading.Thread(
        target=run_manual_in_thread,
        args=(scenario_ids, environment_id, headless),
        daemon=True
    )
    thread.start()

    return RedirectResponse(url="/suite-runs", status_code=303)


# ── Wątki ────────────────────────────────────────────────────────────────────

def run_suite_in_thread(suite_id: int, environment_id: int, workers_override, headless: bool):
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_suite_background(suite_id, environment_id, workers_override, headless))


def run_manual_in_thread(scenario_ids: list, environment_id: int, headless: bool):
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_manual_background(scenario_ids, environment_id, headless))


# ── Funkcje background ────────────────────────────────────────────────────────

async def run_suite_background(suite_id: int, environment_id: int, workers_override, headless: bool):
    db = SessionLocal()
    try:
        suite = db.query(Suite).filter_by(id=suite_id).first()
        environment = db.query(Environment).filter_by(id=environment_id).first()

        if not suite or not environment:
            return

        suite_scenarios = (
            db.query(SuiteScenario)
            .filter_by(suite_id=suite.id, is_active=True)
            .order_by(SuiteScenario.order)
            .all()
        )
        scenarios = [ss.scenario for ss in suite_scenarios if ss.scenario.is_active]

        if not scenarios:
            return

        workers = workers_override or suite.workers

        executor = SuiteExecutor(
            suite=suite,
            environment=environment,
            scenarios=scenarios,
            workers=workers,
            headless=headless,
            db=db
        )
        await executor.run()

    finally:
        db.close()


async def run_manual_background(scenario_ids: list, environment_id: int, headless: bool):
    db = SessionLocal()
    try:
        environment = db.query(Environment).filter_by(id=environment_id).first()
        if not environment:
            return

        scenarios = (
            db.query(Scenario)
            .filter(Scenario.id.in_(scenario_ids), Scenario.is_active == True)
            .all()
        )
        if not scenarios:
            return

        # Pobierz lub utwórz suite "Manual Runs"
        manual_suite = get_or_create_manual_suite(db)

        executor = SuiteExecutor(
            suite=manual_suite,
            environment=environment,
            scenarios=scenarios,
            workers=len(scenarios),  # każdy scenariusz osobno
            headless=headless,
            db=db
        )
        await executor.run()

    finally:
        db.close()
