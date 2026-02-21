from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class BasePage:
    """
    Klasa bazowa dla wszystkich Page Objects.
    Playwright jest TYLKO tutaj i w klasach dziedziczacych.
    """

    def __init__(self, page: Page):
        self.page = page

    async def wait_for_load(self):
        """
        Czeka az strona sie zaladuje.
        Uzywamy domcontentloaded zamiast networkidle —
        networkidle czeka az ustanie CALY ruch sieciowy co na
        dynamicznych stronach (Amazon, sklepy) moze nigdy nie nastapic.
        """
        await self.page.wait_for_load_state("domcontentloaded")
        # Dodatkowe 1.5s na doladowanie dynamicznych elementow JS
        await self.page.wait_for_timeout(1500)

    async def take_screenshot(self, name: str, run_dir: str):
        path = f"{run_dir}/{name}.png"
        await self.page.screenshot(path=path)
        logger.info(f"Screenshot zapisany: {path}")
        return path

    async def get_text(self, selector: str) -> str | None:
        try:
            element = self.page.locator(selector).first
            await element.wait_for(timeout=5000)
            return (await element.text_content() or "").strip()
        except Exception:
            return None

    async def is_visible(self, selector: str) -> bool:
        try:
            return await self.page.locator(selector).first.is_visible()
        except Exception:
            return False

    async def click(self, selector: str):
        await self.page.locator(selector).first.click()
        await self.wait_for_load()
