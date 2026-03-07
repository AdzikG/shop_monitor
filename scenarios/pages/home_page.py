"""
Page objects dla wszystkich etapów.
Każdy page dostaje (page, context, instructions) gdzie instructions
to dict produkowany przez rules poprzedniego etapu.
"""
from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import HomeData


# ── HomePage ──────────────────────────────────────────────────────────────────

class HomePage(BasePage):

    class Cookies:
        BTN_ACCEPT = Sel(desktop=('role', 'button', {'name': 'Akceptuję'}))

    async def execute(self, instructions: dict) -> HomeData:
        await self.page.goto(self.context.environment_url)
        await self.wait_for_navigation()
        await self._accept_cookies()

        if self.is_mobile:
            await self._close_app_banner()

        return HomeData(loaded=True)

    async def _accept_cookies(self):
        if await self.is_visible(self.Cookies.BTN_ACCEPT):
            await self.sloc(self.Cookies.BTN_ACCEPT).click()

    async def _close_app_banner(self):
        # Hook — nadpisz jeśli sklep pokazuje banner aplikacji mobilnej
        pass
