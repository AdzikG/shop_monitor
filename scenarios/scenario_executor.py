"""
Scenario Executor — uruchamia pojedynczy scenariusz testowy.
Używa ScenarioContext + ShopRunner zamiast bezpośrednich wywołań Playwright.
"""

import logging
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from app.models.run import ScenarioRun, RunStatus
from app.models.scenario import Scenario
from app.models.environment import Environment
from core.alert_engine import AlertEngine
from scenarios.context import ScenarioContext
from scenarios.shop_runner import ShopRunner

logger = logging.getLogger(__name__)


class ScenarioExecutor:
    """Wykonuje pojedynczy scenariusz testowy przez Playwright."""

    def __init__(
        self,
        scenario_db: Scenario,
        environment_db: Environment,
        suite_run_id: int,
        suite_id: int,
        db: Session,
        headless: bool = True,
    ):
        self.scenario_db = scenario_db
        self.environment_db = environment_db
        self.suite_run_id = suite_run_id
        self.suite_id = suite_id
        self.db = db
        self.headless = headless
        self.scenario_run = None
        self.alert_engine = None

    async def run(self) -> ScenarioRun:
        """Uruchamia scenariusz i zwraca ScenarioRun z wynikami."""

        # Buduj context z danych DB
        context = ScenarioContext.from_db(self.scenario_db, self.environment_db)

        # Utwórz scenario_run w bazie
        self.scenario_run = ScenarioRun(
            suite_id=self.suite_id,
            suite_run_id=self.suite_run_id,
            scenario_id=self.scenario_db.id,
            environment_id=self.environment_db.id,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(self.scenario_run)
        self.db.commit()
        self.db.refresh(self.scenario_run)

        # Inicjalizuj AlertEngine
        self.alert_engine = AlertEngine(
            run_id=self.scenario_run.id,
            scenario_id=self.scenario_db.id,
            environment_id=self.environment_db.id,
            db=self.db,
        )

        logger.info(f"[RUN #{self.scenario_run.id}] Start: {self.scenario_db.name}")

        try:
            await self._execute(context)

            if self.alert_engine.counted_alerts() > 0:
                self.scenario_run.status = RunStatus.FAILED
            else:
                self.scenario_run.status = RunStatus.SUCCESS

        except Exception as e:
            logger.error(f"[RUN #{self.scenario_run.id}] Nieoczekiwany błąd: {e}", exc_info=True)
            self.scenario_run.status = RunStatus.FAILED
            self.alert_engine.add_alert("scenario.unexpected_error", description=str(e))

        finally:
            self.alert_engine.save_all()
            self.scenario_run.finished_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.info(
                f"[RUN #{self.scenario_run.id}] Finished: {self.scenario_run.status.value} | "
                f"Duration: {self.scenario_run.duration_seconds}s | "
                f"Alerts: {self.alert_engine.counted_alerts()}"
            )

        return self.scenario_run

    async def _execute(self, context: ScenarioContext):
        """Uruchamia Playwright i przekazuje sterowanie do ShopRunner."""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            browser_context = await browser.new_context(
                # Mobile viewport jeśli flaga ustawiona
                viewport={'width': 390, 'height': 844} if context.is_mobile else {'width': 1280, 'height': 720},
            )
            page = await browser_context.new_page()

            try:
                runner = ShopRunner(page=page, context=context)
                result = await runner.run()

                # Przekaż alerty z ShopRunner do AlertEngine
                for alert in result.alerts:
                    self.alert_engine.add_alert(
                        business_rule=alert.business_rule,
                        description=alert.description,
                        alert_type=alert.alert_type,
                    )

                # Zapisz gdzie test się zatrzymał
                if result.stopped_at:
                    logger.info(
                        f"[RUN #{self.scenario_run.id}] "
                        f"Zatrzymano na: {result.stopped_at} | "
                        f"Sukces: {result.success}"
                    )

                # Test zatrzymał się nieoczekiwanie = błąd
                if result.stopped_at and not result.success:
                    self.scenario_run.status = RunStatus.FAILED

            finally:
                await browser_context.close()
                await browser.close()
