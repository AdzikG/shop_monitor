from scenarios.pages.base_page import BasePage
from scenarios.run_data import Cart0Data

# ── Cart0Page — lista produktów ───────────────────────────────────────────────

class Cart0Page(BasePage):
    TOTAL_PRICE = ('locator', '.cart-total .price')
    CART_ITEM   = ('locator', '.cart-item')
    BTN_NEXT    = ('role', 'button', {'name': 'Dalej'})

    async def execute(self, instructions: dict) -> Cart0Data:
        await self.wait_for_navigation()

        total = await self.get_decimal(self.TOTAL_PRICE)
        count = await self.loc(self.CART_ITEM).count()

        if self.context.is_order:
            await self.loc(self.BTN_NEXT).click()
            await self.wait_for_navigation()

        return Cart0Data(total_price=total, item_count=count)