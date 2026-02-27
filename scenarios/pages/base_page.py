from playwright.async_api import Page
from scenarios.context import ScenarioContext
import logging
import re

logger = logging.getLogger(__name__)


class BasePage:
    def __init__(self, page: Page, context: ScenarioContext):
        self.page = page
        self.context = context

    # ── Lokator ───────────────────────────────────────────────────────────────

    def loc(self, selector: tuple):
        """
        Interpretuje tuple selektora i zwraca Playwright Locator.

        Formaty:
          ('locator',      'css_or_xpath')
          ('role',         'button',       {'name': 'Dodaj'})
          ('text',         'Kup teraz',    {'exact': True})
          ('test_id',      'add-to-cart')
          ('label',        'Kod pocztowy')
          ('placeholder',  'Wpisz kod...')
        """
        kind = selector[0]

        if kind == 'locator':
            return self.page.locator(selector[1])
        elif kind == 'role':
            kwargs = selector[2] if len(selector) > 2 else {}
            return self.page.get_by_role(selector[1], **kwargs)
        elif kind == 'text':
            kwargs = selector[2] if len(selector) > 2 else {}
            return self.page.get_by_text(selector[1], **kwargs)
        elif kind == 'test_id':
            return self.page.get_by_test_id(selector[1])
        elif kind == 'label':
            return self.page.get_by_label(selector[1])
        elif kind == 'placeholder':
            return self.page.get_by_placeholder(selector[1])
        else:
            raise ValueError(f"Nieznany typ selektora: {kind}")

    # ── Desktop / mobile ──────────────────────────────────────────────────────

    @property
    def is_mobile(self) -> bool:
        return self.context.is_mobile

    @property
    def is_desktop(self) -> bool:
        return self.context.is_desktop

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def wait_for_navigation(self):
        await self.page.wait_for_load_state('networkidle')

    async def safe_click(self, selector: tuple):
        el = self.loc(selector)
        await el.scroll_into_view_if_needed()
        await el.click()

    async def safe_fill(self, selector: tuple, value: str):
        el = self.loc(selector)
        await el.clear()
        await el.fill(value)

    async def get_text(self, selector: tuple) -> str | None:
        try:
            return (await self.loc(selector).inner_text()).strip()
        except Exception:
            return None

    async def get_decimal(self, selector: tuple) -> float | None:
        text = await self.get_text(selector)
        if not text:
            return None
        cleaned = re.sub(r'[^\d,.]', '', text).replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return None

    async def is_visible(self, selector: tuple) -> bool:
        try:
            return await self.loc(selector).is_visible()
        except Exception:
            return False

    def log(self, msg: str):
        logger.info(f"[{self.__class__.__name__}] {msg}")
