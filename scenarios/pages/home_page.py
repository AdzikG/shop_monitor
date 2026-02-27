"""
Page objects dla wszystkich etapów.
Każdy page dostaje (page, context, instructions) gdzie instructions
to dict produkowany przez rules poprzedniego etapu.
"""
from scenarios.pages.base_page import BasePage
from scenarios.run_data import HomeData

# ── HomePage ──────────────────────────────────────────────────────────────────

class HomePage(BasePage):
    COOKIE_ACCEPT = ('role', 'button', {'name': 'Akceptuję'})

    async def execute(self, instructions: dict) -> HomeData:
        await self.page.goto(self.context.environment_url)
        await self.wait_for_navigation()
        await self._accept_cookies()

        if self.is_mobile:
            await self._close_app_banner()

        return HomeData(loaded=True)

    async def _accept_cookies(self):
        if await self.is_visible(self.COOKIE_ACCEPT):
            await self.loc(self.COOKIE_ACCEPT).click()

    async def _close_app_banner(self):
        # Hook — nadpisz w MobileHomePage jeśli masz banner
        pass