from scenarios.pages.base_page import BasePage
from scenarios.run_data import Cart2Data

# ── Cart2Page — płatności ─────────────────────────────────────────────────────

class Cart2Page(BasePage):
    PAYMENT_OPTION = ('locator', '.payment-option')
    PAYMENT_NAME   = ('locator', '.payment-option .name')
    PAYMENT_PRICE  = ('locator', '.payment-option .price')
    BTN_NEXT       = ('role', 'button', {'name': 'Dalej'})

    async def execute(self, instructions: dict) -> Cart2Data:
        await self.wait_for_navigation()

        available = await self._get_available_options()
        selected  = await self._select_payment()
        price     = await self.get_decimal(self.PAYMENT_PRICE)

        if self.context.is_order and selected:
            await self.loc(self.BTN_NEXT).click()
            await self.wait_for_navigation()

        return Cart2Data(
            available_options=available,
            selected=selected,
            price=price,
        )

    async def _get_available_options(self) -> list[str]:
        names = []
        for el in await self.loc(self.PAYMENT_NAME).all():
            names.append((await el.inner_text()).strip())
        return names

    async def _select_payment(self) -> str | None:
        if not self.context.payment_name:
            return None
        option = self.page.locator('.payment-option').filter(
            has_text=self.context.payment_name
        )
        if await option.count() > 0:
            await option.first.click()
            return self.context.payment_name
        return None
