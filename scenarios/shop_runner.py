"""
ShopRunner — główny orkiestrator testu.
Odpowiedzialności:
  1. Uruchamia pages w odpowiedniej kolejności
  2. Przekazuje instructions między etapami (rules → pages)
  3. Obsługuje zatrzymanie testu (StopTest)
  4. Zbiera alerty ze wszystkich etapów
"""
import logging
from dataclasses import dataclass, field

from playwright.async_api import Page

from scenarios.context import ScenarioContext
from scenarios.run_data import RunData
from scenarios.rules_result import AlertResult, RulesResult

# Pages
from scenarios.pages.pages import (
    HomePage, ListingPage,
    Cart0Page, Cart1Page, Cart2Page, Cart3Page, Cart4Page,
)

# Rules
from scenarios.rules.rules import (
    HomeRules, ListingRules,
    Cart0Rules, Cart1Rules, Cart2Rules, Cart3Rules, Cart4Rules,
    GlobalRules,
)

logger = logging.getLogger(__name__)


@dataclass
class ShopRunResult:
    run_data: RunData
    alerts: list[AlertResult] = field(default_factory=list)
    stopped_at: str | None = None
    success: bool = True


class StopTest(Exception):
    """
    Rzucane gdy test ma się zatrzymać.
    expected=True  → stop był oczekiwany (flaga stop_at_cartX lub reguła negatywna)
    expected=False → stop oznacza błąd (dotarł do etapu gdzie nie powinien)
    """
    def __init__(self, stage: str, reason: str, expected: bool = True):
        self.stage = stage
        self.reason = reason
        self.expected = expected


class ShopRunner:
    def __init__(self, page: Page, context: ScenarioContext):
        self.page = page
        self.context = context
        self.run_data = RunData()
        self.alerts: list[AlertResult] = []
        # Instrukcje akumulowane między etapami
        self.instructions: dict = {}

    # ── Publiczne API ─────────────────────────────────────────────────────────

    async def run(self) -> ShopRunResult:
        try:
            await self._run_home()
            await self._run_listing()
            await self._run_cart0()

            if self.context.is_order:
                await self._run_cart1()
                await self._run_cart2()
                await self._run_cart3()
                await self._run_cart4()

            # Global rules — mają dostęp do danych ze wszystkich etapów
            global_result = GlobalRules(self.context).check(self.run_data)
            self._process_result(global_result, 'global')

        except StopTest as e:
            if e.expected:
                logger.info(
                    f"[{self.context.scenario_name}] "
                    f"Test zatrzymany na '{e.stage}': {e.reason}"
                )
            else:
                logger.warning(
                    f"[{self.context.scenario_name}] "
                    f"Test przerwany na '{e.stage}' (nieoczekiwane): {e.reason}"
                )
            return ShopRunResult(
                run_data=self.run_data,
                alerts=self.alerts,
                stopped_at=e.stage,
                success=e.expected,
            )

        except Exception as e:
            logger.exception(f"[{self.context.scenario_name}] Nieoczekiwany błąd: {e}")
            return ShopRunResult(
                run_data=self.run_data,
                alerts=self.alerts,
                stopped_at='error',
                success=False,
            )

        return ShopRunResult(
            run_data=self.run_data,
            alerts=self.alerts,
            success=True,
        )

    # ── Etapy ─────────────────────────────────────────────────────────────────

    async def _run_home(self):
        self.run_data.home = await self._get_page(HomePage).execute(self.instructions)
        self._process_result(HomeRules(self.context).check(self.run_data), 'home')

    async def _run_listing(self):
        self.run_data.listing = await self._get_page(ListingPage).execute(self.instructions)
        self._process_result(ListingRules(self.context).check(self.run_data), 'listing')

    async def _run_cart0(self):
        self.run_data.cart0 = await self._get_page(Cart0Page).execute(self.instructions)
        self._process_result(Cart0Rules(self.context).check(self.run_data), 'cart0')

    async def _run_cart1(self):
        self.run_data.cart1 = await self._get_page(Cart1Page).execute(self.instructions)
        self._process_result(Cart1Rules(self.context).check(self.run_data), 'cart1')

        if self.context.flag('stop_at_cart1'):
            raise StopTest('cart1', 'Oczekiwane zatrzymanie na cart1', expected=True)

    async def _run_cart2(self):
        self.run_data.cart2 = await self._get_page(Cart2Page).execute(self.instructions)
        self._process_result(Cart2Rules(self.context).check(self.run_data), 'cart2')

        if self.context.flag('stop_at_cart2'):
            raise StopTest('cart2', 'Oczekiwane zatrzymanie na cart2', expected=True)

    async def _run_cart3(self):
        self.run_data.cart3 = await self._get_page(Cart3Page).execute(self.instructions)
        self._process_result(Cart3Rules(self.context).check(self.run_data), 'cart3')

        if self.context.flag('stop_at_cart3'):
            raise StopTest('cart3', 'Oczekiwane zatrzymanie na cart3', expected=True)

    async def _run_cart4(self):
        # Flaga should_not_complete — dotarcie tutaj jest błędem
        if self.context.flag('should_not_complete'):
            raise StopTest(
                stage='cart3',
                reason='Scenariusz nie powinien dotrzeć do podsumowania',
                expected=False,
            )

        self.run_data.cart4 = await self._get_page(Cart4Page).execute(self.instructions)
        self._process_result(Cart4Rules(self.context).check(self.run_data), 'cart4')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_page(self, desktop_cls, mobile_cls=None):
        """Zwraca odpowiednią klasę page dla desktop/mobile."""
        if self.context.is_mobile and mobile_cls:
            return mobile_cls(self.page, self.context)
        return desktop_cls(self.page, self.context)

    def _process_result(self, result: RulesResult, stage: str):
        """
        Przetwarza wynik rules:
        - Zapisuje alerty
        - Akumuluje instrukcje dla kolejnych pages
        - Rzuca StopTest jeśli rules zdecydowały o zatrzymaniu
        """
        for alert in result.alerts:
            logger.warning(f"[{stage}] ALERT: {alert.business_rule} — {alert.title}")
        self.alerts.extend(result.alerts)

        # Instrukcje są addytywne — kolejne etapy mogą je nadpisywać
        self.instructions.update(result.instructions)

        if result.should_stop:
            raise StopTest(stage=stage, reason=result.stop_reason, expected=True)
