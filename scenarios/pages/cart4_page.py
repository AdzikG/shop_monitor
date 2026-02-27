from scenarios.pages.base_page import BasePage
from scenarios.run_data import Cart4Data

# ── Cart4Page — podsumowanie ──────────────────────────────────────────────────

class Cart4Page(BasePage):
    TOTAL_PRICE    = ('locator', '.summary-total .price')
    DELIVERY_NAME  = ('locator', '.summary-delivery .name')
    DELIVERY_PRICE = ('locator', '.summary-delivery .price')
    PAYMENT_NAME   = ('locator', '.summary-payment .name')
    ORDER_NUMBER   = ('locator', '.order-confirmation .order-number')
    BTN_ORDER      = ('role', 'button', {'name': 'Zamawiam i płacę'})

    async def execute(self, instructions: dict) -> Cart4Data:
        await self.wait_for_navigation()

        total          = await self.get_decimal(self.TOTAL_PRICE)
        delivery_name  = await self.get_text(self.DELIVERY_NAME)
        delivery_price = await self.get_decimal(self.DELIVERY_PRICE)
        payment_name   = await self.get_text(self.PAYMENT_NAME)

        order_number = None
        if self.context.is_order:
            await self._before_order()
            await self.loc(self.BTN_ORDER).click
            await self.wait_for_navigation()
            order_number = await self.get_text(self.ORDER_NUMBER)

        return Cart4Data(
            total_price=total,
            delivery_name=delivery_name,
            delivery_price=delivery_price,
            payment_name=payment_name,
            order_number=order_number,
        )

    async def _before_order(self):
        # Hook — np. akceptacja regulaminu
        pass
