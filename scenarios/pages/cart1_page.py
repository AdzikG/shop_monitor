from scenarios.pages.base_page import BasePage
from scenarios.run_data import Cart1Data

# ── Cart1Page — transporty ────────────────────────────────────────────────────

class Cart1Page(BasePage):
    DELIVERY_OPTION  = ('locator', '.delivery-option')
    DELIVERY_NAME    = ('locator', '.delivery-option .name')
    DELIVERY_DATE    = ('locator', '.delivery-option .estimated-date')
    DELIVERY_CUTOFF  = ('locator', '.delivery-option .cutoff-time')
    DELIVERY_PRICE   = ('locator', '.delivery-option .price')
    POSTAL_CODE_FIELD = ('placeholder', 'Kod pocztowy')
    BTN_NEXT         = ('role', 'button', {'name': 'Dalej'})

    async def execute(self, instructions: dict) -> Cart1Data:
        await self.wait_for_navigation()

        # Faza 1 — zbierz dostępne opcje przed akcją
        available = await self._get_available_options()

        # Faza 2 — wybierz dostawę
        selected = await self._select_delivery()

        # Faza 3 — reaguj na to co pojawiło się po wyborze (page ocenia sam)
        postal_code_required = False
        postal_code_filled = False

        if selected:
            postal_code_required, postal_code_filled = await self._handle_post_selection()

        # Faza 4 — zbierz dane po wszystkich akcjach
        date   = await self.get_text(self.DELIVERY_DATE)
        cutoff = await self.get_text(self.DELIVERY_CUTOFF)
        price  = await self.get_decimal(self.DELIVERY_PRICE)

        if self.context.is_order and selected:
            await self.loc(self.BTN_NEXT).click()
            await self.wait_for_navigation()

        return Cart1Data(
            available_options=available,
            selected=selected,
            estimated_date=date,
            cutoff_time=cutoff,
            price=price,
            postal_code_required=postal_code_required,
            postal_code_filled=postal_code_filled,
        )

    async def _handle_post_selection(self) -> tuple[bool, bool]:
        """
        Reaguje na to co pojawiło się po wyborze dostawy.
        Page sam ocenia sytuację na podstawie tego co widzi.
        Zwraca: (postal_code_required, postal_code_filled)
        """
        postal_code_required = await self.is_visible(self.POSTAL_CODE_FIELD)
        postal_code_filled = False

        if postal_code_required:
            if self.context.postal_code:
                self.log(f"Pole kodu pocztowego widoczne — wpisuję {self.context.postal_code}")
                await self.safe_fill(self.POSTAL_CODE_FIELD, self.context.postal_code)
                await self.wait_for_navigation()
                postal_code_filled = True
            else:
                self.log("Pole kodu pocztowego widoczne — brak kodu w context")

        if self.is_desktop:
            await self._handle_desktop_post_selection()

        return postal_code_required, postal_code_filled

    async def _handle_desktop_post_selection(self):
        # Hook — np. popup z potwierdzeniem na desktop
        pass

    async def _get_available_options(self) -> list[str]:
        names = []
        for el in await self.loc(self.DELIVERY_NAME).all():
            names.append((await el.inner_text()).strip())
        return names

    async def _select_delivery(self) -> str | None:
        if not self.context.delivery_name:
            return None
        option = self.page.locator('.delivery-option').filter(
            has_text=self.context.delivery_name
        )
        if await option.count() > 0:
            await option.first.click()
            return self.context.delivery_name
        return None
