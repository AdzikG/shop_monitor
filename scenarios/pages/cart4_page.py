from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import Cart4Data


# ── Cart4Page — podsumowanie ──────────────────────────────────────────────────

class Cart4Page(BasePage):

    # ── Podsumowanie zamówienia ───────────────────────────────────────────────

    class Summary:
        TOTAL_PRICE    = Sel(desktop=('locator', '.summary-total .price'))
        DELIVERY_NAME  = Sel(desktop=('locator', '.summary-delivery .name'))
        DELIVERY_PRICE = Sel(desktop=('locator', '.summary-delivery .price'))
        PAYMENT_NAME   = Sel(desktop=('locator', '.summary-payment .name'))

    # ── Potwierdzenie złożenia zamówienia ─────────────────────────────────────

    class Confirmation:
        ORDER_NUMBER = Sel(desktop=('locator', '.order-confirmation .order-number'))

    # ── Nawigacja ─────────────────────────────────────────────────────────────

    class Nav:
        BTN_ORDER = Sel(desktop=('role', 'button', {'name': 'Zamawiam i płacę'}))

    # ── Główna logika ─────────────────────────────────────────────────────────

    async def execute(self, instructions: dict) -> Cart4Data:
        await self.wait_for_navigation()

        total          = await self.get_decimal(self.Summary.TOTAL_PRICE)
        delivery_name  = await self.get_text(self.Summary.DELIVERY_NAME)
        delivery_price = await self.get_decimal(self.Summary.DELIVERY_PRICE)
        payment_name   = await self.get_text(self.Summary.PAYMENT_NAME)

        order_number = None
        if self.scenario_context.is_order:
            await self._before_order()
            await self.sloc(self.Nav.BTN_ORDER).click()
            await self.wait_for_navigation()
            order_number = await self.get_text(self.Confirmation.ORDER_NUMBER)

        return Cart4Data(
            total_price=total,
            delivery_name=delivery_name,
            delivery_price=delivery_price,
            payment_name=payment_name,
            order_number=order_number,
        )

    # ── Sekcja: przed złożeniem ───────────────────────────────────────────────

    async def _before_order(self):
        # Hook — np. akceptacja regulaminu przed kliknięciem "Zamawiam"
        pass
