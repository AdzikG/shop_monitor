from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncio
import threading
import sys

from database import SessionLocal, get_db
from app.models.suite import Suite
from app.models.environment import Environment
from app.models.suite_scenario import SuiteScenario
from scenarios.suite_executor import SuiteExecutor
from app.templates import templates

router = APIRouter(tags=["execute"])


@router.get("/execute")
async def execute_form(request: Request, db: Session = Depends(get_db)):
    """Formularz wyboru suite i environment do uruchomienia."""
    suites = db.query(Suite).filter(Suite.is_active == True).all()
    environments = db.query(Environment).filter(Environment.is_active == True).all()
    
    return templates.TemplateResponse("execute_form.html", {
        "request": request,
        "suites": suites,
        "environments": environments,
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
    
    return RedirectResponse(url="/dashboard", status_code=303)


def run_suite_in_thread(suite_id: int, environment_id: int, workers_override: int | None, headless: bool):
    """Uruchamia suite w nowej petli asyncio."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(run_suite_background(suite_id, environment_id, workers_override, headless))


async def run_suite_background(suite_id: int, environment_id: int, workers_override: int | None, headless: bool):
    """Wykonuje suite przez SuiteExecutor."""
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
