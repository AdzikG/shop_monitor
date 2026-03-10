from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import Cart0Data
from core.config import TestAccountName


# ── Cart0Page — podsumowanie koszyka ─────────────────────────────────────────

class Cart0Page(BasePage):

    # ── Koszyk ────────────────────────────────────────────────────────────────

    class Cart:
        TOTAL_PRICE = Sel(desktop=('locator', '.cart-total .price'))
        ITEM        = Sel(desktop=('locator', '.cart-item'))
        BTN_NEXT    = Sel(desktop=('role', 'button', {'name': 'Dalej'}))

    # ── Gwarancja ─────────────────────────────────────────────────────────────

    class Warranty:
        SECTION  = Sel(desktop=('locator', '.warranty-section'))
        CHECKBOX = Sel(desktop=('label', 'Gwarancja'))
        BTN_ADD  = Sel(desktop=('role', 'button', {'name': 'Dodaj gwarancję'}))
        PRICE    = Sel(desktop=('locator', '.warranty-price'))

    # ── Usługi ────────────────────────────────────────────────────────────────

    class Services:
        SECTION  = Sel(desktop=('locator', '.services-section'))
        BTN_ADD  = Sel(desktop=('role', 'button', {'name': 'Dodaj usługę'}))

    # ── Promocja ──────────────────────────────────────────────────────────────

    class Promo:
        FIELD_CODE = Sel(desktop=('placeholder', 'Kod promocyjny'))
        BTN_APPLY  = Sel(desktop=('role', 'button', {'name': 'Zastosuj'}))
        LABEL_OK   = Sel(desktop=('locator', '.promo-success'))
        LABEL_ERR  = Sel(desktop=('locator', '.promo-error'))

    # ── Główna logika ─────────────────────────────────────────────────────────

    async def execute(self, instructions: dict) -> Cart0Data:
        await self.wait_for_navigation()

        total = await self.get_decimal(self.Cart.TOTAL_PRICE)
        count = await self.sloc(self.Cart.ITEM).count()

        if self.scenario_context.is_order:
            await self.sloc(self.Cart.BTN_NEXT).click()
            await self.wait_for_navigation()

        return Cart0Data(total_price=total, item_count=count)
