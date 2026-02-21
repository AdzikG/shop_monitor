"""
Shop Monitor
============
Uruchamia scenariusze z bazy danych rownolegnie z uzyciem asyncio.

Uzycie:
    python main.py                          # wszystkie aktywne scenariusze
    python main.py --suite 1                # konkretna suite
    python main.py --scenario 1             # TYLKO jeden scenariusz 
    python main.py --environment 1          # konkretne srodowisko
    python main.py --workers 4              # nadpisz liczbe workers
    python main.py --headless               # bez okna przegladarki
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from database import SessionLocal, engine
from app.models import Base
from app.models.scenario import Scenario
from app.models.suite import Suite
from app.models.environment import Environment
from app.models.suite_scenario import SuiteScenario
from app.models.suite_run import SuiteRun, SuiteRunStatus
from scenarios.scenario_executor import ScenarioExecutor

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    suite_id = None
    scenario_id = None
    environment_id = None
    workers = None
    headless = "--headless" in sys.argv

    if "--suite" in sys.argv:
        idx = sys.argv.index("--suite")
        suite_id = int(sys.argv[idx + 1])
    
    if "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        scenario_id = int(sys.argv[idx + 1])

    if "--environment" in sys.argv:
        idx = sys.argv.index("--environment")
        environment_id = int(sys.argv[idx + 1])

    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        workers = int(sys.argv[idx + 1])

    return suite_id, scenario_id, environment_id, workers, headless


def load_from_db(db: Session, suite_id: int | None, scenario_id: int | None, environment_id: int | None):
    """
    Wczytuje scenariusze z bazy.
    
    Jesli scenario_id — uruchamia TYLKO ten scenariusz.
    Jesli suite_id — uruchamia cala suite.
    Inaczej — pierwsza aktywna suite.
    """
    
    # Znajdz srodowisko
    if environment_id:
        environment = db.query(Environment).filter_by(id=environment_id, is_active=True).first()
    else:
        environment = db.query(Environment).filter_by(is_active=True).first()

    if not environment:
        logger.error("Brak aktywnych srodowisk w bazie.")
        sys.exit(1)
    
    # Pojedynczy scenariusz
    if scenario_id:
        scenario = db.query(Scenario).filter_by(id=scenario_id, is_active=True).first()
        if not scenario:
            logger.error(f"Scenariusz #{scenario_id} nie istnieje lub nieaktywny.")
            sys.exit(1)
        
        # Znajdz suite dla tego scenariusza (pierwsza w ktorej jest)
        suite_scenario = db.query(SuiteScenario).filter_by(scenario_id=scenario_id, is_active=True).first()
        if not suite_scenario:
            logger.error(f"Scenariusz #{scenario_id} nie nalezy do zadnej suite.")
            sys.exit(1)
        
        suite = suite_scenario.suite
        scenarios = [scenario]
        
        logger.info(f"Tryb: POJEDYNCZY SCENARIUSZ #{scenario.id}")
        return suite, environment, scenarios
    
    # Cala suite
    if suite_id:
        suite = db.query(Suite).filter_by(id=suite_id, is_active=True).first()
    else:
        suite = db.query(Suite).filter_by(is_active=True).first()

    if not suite:
        logger.error("Brak aktywnych suite w bazie.")
        sys.exit(1)

    suite_scenarios = (
        db.query(SuiteScenario)
        .filter_by(suite_id=suite.id, is_active=True)
        .order_by(SuiteScenario.order)
        .all()
    )

    scenarios = [ss.scenario for ss in suite_scenarios if ss.scenario.is_active]
    
    logger.info(f"Tryb: CALA SUITE '{suite.name}'")
    return suite, environment, scenarios


async def run_single_scenario(scenario, suite, environment, headless: bool):
    """Uruchamia pojedynczy scenariusz z prostym suite_run."""
    
    db = SessionLocal()
    
    try:
        # Utworz suite_run (nawet dla pojedynczego scenariusza)
        suite_run = SuiteRun(
            suite_id=suite.id,
            environment_id=environment.id,
            status=SuiteRunStatus.RUNNING,
            total_scenarios=1,
        )
        db.add(suite_run)
        db.commit()
        db.refresh(suite_run)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[SINGLE RUN #{suite_run.id}] {scenario.name} @ {environment.name}")
        logger.info(f"{'='*60}\n")
        
        # Uruchom scenariusz
        executor = ScenarioExecutor(
            scenario_db=scenario,
            suite_run_id=suite_run.id,
            suite_id=suite.id,
            environment_id=environment.id,
            base_url=environment.base_url,
            db=db,
            headless=headless
        )
        
        result = await executor.run()
        
        # Finalizuj suite_run
        suite_run.success_scenarios = 1 if result.status.value == "success" else 0
        suite_run.failed_scenarios = 0 if result.status.value == "success" else 1
        suite_run.total_alerts = len([a for a in result.alerts if a.is_counted])
        suite_run.finished_at = datetime.now()
        suite_run.status = SuiteRunStatus.SUCCESS if result.status.value == "success" else SuiteRunStatus.FAILED
        
        db.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[COMPLETED] Status: {suite_run.status.value.upper()}")
        logger.info(f"Alerts: {suite_run.total_alerts}")
        logger.info(f"{'='*60}\n")
        
    finally:
        db.close()


async def run_suite(suite, environment, scenarios, workers: int, headless: bool):
    """Uruchamia pelna suite przez SuiteExecutor."""
    
    from scenarios.suite_executor import SuiteExecutor
    
    db = SessionLocal()
    try:
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


if __name__ == "__main__":
    suite_id, scenario_id, environment_id, workers_override, headless = parse_args()

    db = SessionLocal()
    try:
        suite, environment, scenarios = load_from_db(db, suite_id, scenario_id, environment_id)
    finally:
        db.close()
    
    # Pojedynczy scenariusz — prostsza logika
    if scenario_id:
        asyncio.run(run_single_scenario(scenarios[0], suite, environment, headless))
    # Cala suite — SuiteExecutor
    else:
        workers = workers_override or suite.workers
        asyncio.run(run_suite(suite, environment, scenarios, workers, headless))