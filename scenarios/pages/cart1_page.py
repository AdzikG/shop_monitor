from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import Cart1Data


# ── Cart1Page — dostawa ───────────────────────────────────────────────────────

class Cart1Page(BasePage):

    # ── Opcje dostawy ─────────────────────────────────────────────────────────

    class Delivery:
        OPTION         = Sel(desktop=('locator', '.delivery-option'))
        NAME           = Sel(desktop=('locator', '.delivery-option .name'))
        ESTIMATED_DATE = Sel(desktop=('locator', '.delivery-option .estimated-date'))
        CUTOFF_TIME    = Sel(desktop=('locator', '.delivery-option .cutoff-time'))
        PRICE          = Sel(desktop=('locator', '.delivery-option .price'))

    # ── Adres / kod pocztowy ──────────────────────────────────────────────────

    class Address:
        FIELD_POSTAL = Sel(desktop=('placeholder', 'Kod pocztowy'))

    # ── Nawigacja ─────────────────────────────────────────────────────────────

    class Nav:
        BTN_NEXT = Sel(desktop=('role', 'button', {'name': 'Dalej'}))

    # ── Główna logika ─────────────────────────────────────────────────────────

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
        date   = await self.get_text(self.Delivery.ESTIMATED_DATE)
        cutoff = await self.get_text(self.Delivery.CUTOFF_TIME)
        price  = await self.get_decimal(self.Delivery.PRICE)

        if self.scenario_context.is_order and selected:
            await self.sloc(self.Nav.BTN_NEXT).click()
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

    # ── Sekcja: dostawa ───────────────────────────────────────────────────────

    async def _get_available_options(self) -> list[str]:
        names = []
        for el in await self.sloc(self.Delivery.NAME).all():
            names.append((await el.inner_text()).strip())
        return names

    async def _select_delivery(self) -> str | None:
        if not self.scenario_context.delivery_name:
            return None
        option = self.page.locator('.delivery-option').filter(
            has_text=self.scenario_context.delivery_name
        )
        if await option.count() > 0:
            await option.first.click()
            return self.scenario_context.delivery_name
        return None

    # ── Sekcja: post-wybór ────────────────────────────────────────────────────

    async def _handle_post_selection(self) -> tuple[bool, bool]:
        """
        Reaguje na to co pojawiło się po wyborze dostawy.
        Zwraca: (postal_code_required, postal_code_filled)
        """
        postal_code_required = await self.is_visible(self.Address.FIELD_POSTAL)
        postal_code_filled = False

        if postal_code_required:
            if self.scenario_context.postal_code:
                self.log(f"Pole kodu pocztowego widoczne — wpisuję {self.scenario_context.postal_code}")
                await self.safe_fill(self.Address.FIELD_POSTAL, self.scenario_context.postal_code)
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
