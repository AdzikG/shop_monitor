from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import Cart3Data


# ── Cart3Page — adres ─────────────────────────────────────────────────────────

class Cart3Page(BasePage):

    # ── Adres ─────────────────────────────────────────────────────────────────

    class Address:
        FIELD_POSTAL = Sel(desktop=('placeholder', 'Kod pocztowy'))
        FIELD_STREET = Sel(desktop=('placeholder', 'Ulica'))
        FIELD_CITY   = Sel(desktop=('placeholder', 'Miasto'))

    # ── Faktura firmowa ───────────────────────────────────────────────────────

    class Company:
        CHECKBOX = Sel(desktop=('label', 'Zamówienie na firmę'))

    # ── Nawigacja ─────────────────────────────────────────────────────────────

    class Nav:
        BTN_NEXT = Sel(desktop=('role', 'button', {'name': 'Dalej'}))

    # ── Główna logika ─────────────────────────────────────────────────────────

    async def execute(self, instructions: dict) -> Cart3Data:
        await self.wait_for_navigation()

        if instructions.get('fill_company_fields'):
            await self._check_company()

        await self._fill_address()

        if self.scenario_context.is_order:
            await self.sloc(self.Nav.BTN_NEXT).click()
            await self.wait_for_navigation()

        postal = await self.get_text(self.Address.FIELD_POSTAL)
        return Cart3Data(
            postal_code=postal or self.scenario_context.postal_code,
            is_company=instructions.get('fill_company_fields', False),
        )

    # ── Sekcja: adres ─────────────────────────────────────────────────────────

    async def _fill_address(self):
        if self.scenario_context.postal_code:
            if await self.is_visible(self.Address.FIELD_POSTAL):
                await self.safe_fill(self.Address.FIELD_POSTAL, self.scenario_context.postal_code)

    # ── Sekcja: faktura firmowa ───────────────────────────────────────────────

    async def _check_company(self):
        if await self.is_visible(self.Company.CHECKBOX):
            await self.sloc(self.Company.CHECKBOX).check()
