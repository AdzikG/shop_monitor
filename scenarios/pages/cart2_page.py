from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import Cart2Data


# ── Cart2Page — płatności ─────────────────────────────────────────────────────

class Cart2Page(BasePage):

    # ── Opcje płatności ───────────────────────────────────────────────────────

    class Payment:
        OPTION = Sel(desktop=('locator', '.payment-option'))
        NAME   = Sel(desktop=('locator', '.payment-option .name'))
        PRICE  = Sel(desktop=('locator', '.payment-option .price'))

    # ── Nawigacja ─────────────────────────────────────────────────────────────

    class Nav:
        BTN_NEXT = Sel(desktop=('role', 'button', {'name': 'Dalej'}))

    # ── Główna logika ─────────────────────────────────────────────────────────

    async def execute(self, instructions: dict) -> Cart2Data:
        await self.wait_for_navigation()

        available = await self._get_available_options()
        selected  = await self._select_payment()
        price     = await self.get_decimal(self.Payment.PRICE)

        if self.scenario_context.is_order and selected:
            await self.sloc(self.Nav.BTN_NEXT).click()
            await self.wait_for_navigation()

        return Cart2Data(
            available_options=available,
            selected=selected,
            price=price,
        )

    # ── Sekcja: płatność ──────────────────────────────────────────────────────

    async def _get_available_options(self) -> list[str]:
        names = []
        for el in await self.sloc(self.Payment.NAME).all():
            names.append((await el.inner_text()).strip())
        return names

    async def _select_payment(self) -> str | None:
        if not self.scenario_context.payment_name:
            return None
        option = self.page.locator('.payment-option').filter(
            has_text=self.scenario_context.payment_name
        )
        if await option.count() > 0:
            await option.first.click()
            return self.scenario_context.payment_name
        return None
