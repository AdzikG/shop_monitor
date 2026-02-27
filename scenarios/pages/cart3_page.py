from scenarios.pages.base_page import BasePage
from scenarios.run_data import Cart3Data

# ── Cart3Page — adres ─────────────────────────────────────────────────────────

class Cart3Page(BasePage):
    FIELD_POSTAL     = ('placeholder', 'Kod pocztowy')
    FIELD_STREET     = ('placeholder', 'Ulica')
    FIELD_CITY       = ('placeholder', 'Miasto')
    CHECKBOX_COMPANY = ('label', 'Zamówienie na firmę')
    BTN_NEXT         = ('role', 'button', {'name': 'Dalej'})

    async def execute(self, instructions: dict) -> Cart3Data:
        await self.wait_for_navigation()

        # Instrukcja z Cart0Rules
        if instructions.get('fill_company_fields'):
            await self._check_company()

        await self._fill_address()

        # Na mobile adres może być w innym miejscu
        if self.is_mobile:
            await self._fill_mobile_extras()

        if self.context.is_order:
            await self.loc(self.BTN_NEXT).click()
            await self.wait_for_navigation()

        postal = await self.get_text(self.FIELD_POSTAL)
        return Cart3Data(
            postal_code=postal or self.context.postal_code,
            is_company=instructions.get('fill_company_fields', False),
        )

    async def _fill_address(self):
        if self.context.postal_code:
            if await self.is_visible(self.FIELD_POSTAL):
                await self.safe_fill(self.FIELD_POSTAL, self.context.postal_code)

    async def _check_company(self):
        if await self.is_visible(self.CHECKBOX_COMPANY):
            await self.loc(self.CHECKBOX_COMPANY).check()

    async def _fill_mobile_extras(self):
        # Hook — nadpisz w MobileCart3Page jeśli potrzeba
        pass
