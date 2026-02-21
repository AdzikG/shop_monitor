"""
Scenario Executor — uruchamia pojedynczy scenariusz testowy.
"""

import asyncio
import logging
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Page

from sqlalchemy.orm import Session

from app.models.run import ScenarioRun, RunStatus
from app.models.scenario import Scenario
from core.alert_engine import AlertEngine
from pages.cart.cart_0_list import CartListPage

logger = logging.getLogger(__name__)


class ScenarioExecutor:
    """Wykonuje pojedynczy scenariusz testowy przez Playwright."""

    def __init__(
        self,
        scenario_db: Scenario,
        suite_run_id: int,
        suite_id: int,
        environment_id: int,
        base_url: str,
        db: Session,
        headless: bool = True
    ):
        self.scenario_db = scenario_db
        self.suite_run_id = suite_run_id
        self.suite_id = suite_id
        self.environment_id = environment_id
        self.base_url = base_url
        self.db = db
        self.headless = headless
        self.scenario_run = None  # ZMIENIONE z self.run
        self.alert_engine = None

    async def run(self) -> ScenarioRun:
        """Uruchamia scenariusz i zwraca ScenarioRun z wynikami."""
        
        # Utworz scenario_run w bazie
        self.scenario_run = ScenarioRun(
            suite_id=self.suite_id,
            environment_id=self.environment_id,
            suite_run_id=self.suite_run_id,
            scenario_id=self.scenario_db.id,
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
            environment_id=self.environment_id,
            db=self.db
        )

        logger.info(f"[RUN #{self.scenario_run.id}] Start: {self.scenario_db.name}")

        try:
            await self._execute_scenario()
            
            # Sprawdz czy byly alerty
            if self.alert_engine.counted_alerts() > 0:
                self.scenario_run.status = RunStatus.FAILED
            else:
                self.scenario_run.status = RunStatus.SUCCESS
            
        except Exception as e:
            logger.error(f"[RUN #{self.scenario_run.id}] Nieoczekiwany blad: {e}", exc_info=True)
            self.scenario_run.status = RunStatus.FAILED
            self.alert_engine.add_alert(
                "scenario.unexpected_error",
                description=str(e)
            )
        
        finally:
            # Zapisz alerty
            self.alert_engine.save_all()
            
            # Finalizuj run
            self.scenario_run.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(
                f"[RUN #{self.scenario_run.id}] Finished: {self.scenario_run.status.value} | "
                f"Duration: {self.scenario_run.duration_seconds}s | "
                f"Alerts: {self.alert_engine.counted_alerts()}"
            )

        return self.scenario_run  # WAŻNE: zwróć scenario_run

    async def _execute_scenario(self):
        """Glowna logika scenariusza - uruchamia Playwright i przechodzi przez kroki."""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Krok 1: Listing i wybor produktu
                await self._step_listing(page)
                
                # Krok 2: Dodanie do koszyka
                # await self._step_add_to_cart(page)
                
                # Krok 3: Transport
                # await self._step_transport(page)
                
                # etc...
                
            finally:
                await context.close()
                await browser.close()

    async def _step_listing(self, page: Page):
        """Krok 1: Wejscie na listing i wybor produktu."""
        
        cart_page = CartListPage(page)
        
        # Losuj URL z listy
        import random
        listing_url = random.choice(self.scenario_db.listing_urls)
        full_url = f"{self.base_url}{listing_url}"
        
        logger.info(f"[RUN #{self.scenario_run.id}] Listing: {full_url}")
        
        # Przejdz na listing
        await cart_page.go_to_listing(full_url)
        
        # Wybierz losowy produkt
        product = await cart_page.pick_random_product()
        
        if not product:
            # Brak produktow - alert
            self.alert_engine.add_alert("listing.no_products")
            return
        
        logger.info(f"[RUN #{self.scenario_run.id}] Wybrany produkt: {product.get('name', 'N/A')}")
        
        # Zapisz dane produktu w run
        self.scenario_run.product_id = product.get('id')
        self.scenario_run.product_name = product.get('name')
        self.db.flush()
        
        # Przejdz do produktu
        if product.get('url'):
            await page.goto(product['url'])
            await cart_page.wait_for_load()

    async def _step_add_to_cart(self, page: Page):
        """Krok 2: Dodanie produktu do koszyka."""
        
        cart_page = CartListPage(page)
        
        # Kliknij "Dodaj do koszyka"
        success = await cart_page.add_to_cart()
        
        if not success:
            # Przycisk niewidoczny
            self.alert_engine.add_alert("cart.add_to_cart_failed")
            return
        
        logger.info(f"[RUN #{self.scenario_run.id}] Dodano do koszyka")
        
        # Czekaj na potwierdzenie
        await asyncio.sleep(2)