"""
Scenario Executor — uruchamia pojedynczy scenariusz testowy.
Używa ScenarioContext + ShopRunner zamiast bezpośrednich wywołań Playwright.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from app.models.api_error import ApiError
from app.models.api_error_exclusion import ApiErrorExclusion
from app.models.basket_snapshot import BasketSnapshot
from app.models.run import ScenarioRun, RunStatus
from app.models.scenario import Scenario
from app.models.environment import Environment
from core.alert_engine import AlertEngine
from scenarios.context import ScenarioContext
from scenarios.shop_runner import ShopRunner, ShopRunResult

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

        context = ScenarioContext.from_db(self.scenario_db, self.environment_db)

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
                viewport={'width': 390, 'height': 844} if context.is_mobile else {'width': 1280, 'height': 720},
            )
            page = await browser_context.new_page()

            try:
                screenshot_dir = f"screenshots/{self.suite_run_id}/{self.scenario_run.id}"
                Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

                exclusions = [
                    {
                        'endpoint_pattern':      e.endpoint_pattern,
                        'status_code':           e.status_code,
                        'response_body_pattern': e.response_body_pattern,
                    }
                    for e in self.db.query(ApiErrorExclusion).all()
                ]
                runner = ShopRunner(page=page, context=context, screenshot_dir=screenshot_dir, api_error_exclusions=exclusions)
                result = await runner.run()

                self._save_run_data(result)

                for alert in result.alerts:
                    self.alert_engine.add_alert(
                        business_rule=alert.business_rule,
                        description=alert.description,
                        alert_type=alert.alert_type,
                    )

                if result.stopped_at:
                    logger.info(
                        f"[RUN #{self.scenario_run.id}] "
                        f"Zatrzymano na: {result.stopped_at} | "
                        f"Sukces: {result.success}"
                    )

                # Nieoczekiwany stop = rzuć wyjątek żeby run dostał status FAILED
                if not result.success:
                    raise Exception(
                        f"Test zatrzymany nieoczekiwanie na '{result.stopped_at}'"
                    )

            finally:
                await browser_context.close()
                await browser.close()

    def _save_run_data(self, result: ShopRunResult) -> None:
        rd = result.run_data

        if rd.listing and rd.listing.name:
            self.scenario_run.product_name = rd.listing.name

        if result.screenshots:
            last = list(result.screenshots.values())[-1]
            self.scenario_run.screenshot_url = last

        snapshots = []
        if rd.home:
            snapshots.append(BasketSnapshot(
                run_id=self.scenario_run.id,
                stage='home',
                total_price=None,
                raw_data={'screenshot': result.screenshots.get('home')},
            ))
        if rd.listing:
            snapshots.append(BasketSnapshot(
                run_id=self.scenario_run.id,
                stage='listing',
                total_price=None,
                raw_data={'screenshot': result.screenshots.get('listing')},
            ))
        if rd.cart0:
            snapshots.append(BasketSnapshot(
                run_id=self.scenario_run.id,
                stage='cart0',
                total_price=rd.cart0.total_price,
                raw_data={'screenshot': result.screenshots.get('cart0')},
            ))
        if rd.cart1:
            snapshots.append(BasketSnapshot(
                run_id=self.scenario_run.id,
                stage='cart1',
                delivery_price=rd.cart1.price,
                raw_data={'screenshot': result.screenshots.get('cart1')},
            ))
        if rd.cart4:
            snapshots.append(BasketSnapshot(
                run_id=self.scenario_run.id,
                stage='cart4',
                total_price=rd.cart4.total_price,
                delivery_price=rd.cart4.delivery_price,
                raw_data={'screenshot': result.screenshots.get('cart4')},
            ))
        if snapshots:
            self.db.add_all(snapshots)

        for err in result.api_errors:
            body = err.get('response_body')
            if body and len(body) > 250:
                body = body[:250]
            self.db.add(ApiError(
                run_id=self.scenario_run.id,
                endpoint=err['endpoint'],
                method=err['method'],
                status_code=err['status_code'],
                response_body=body,
            ))
