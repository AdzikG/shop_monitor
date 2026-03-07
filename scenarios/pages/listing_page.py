import random
from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import ProductData


# ── ListingPage ───────────────────────────────────────────────────────────────

class ListingPage(BasePage):

    class Product:
        NAME  = Sel(desktop=('locator', '.product-item .product-name'))
        PRICE = Sel(desktop=('locator', '.product-item .product-price'))

    class Actions:
        BTN_ADD_TO_CART = Sel(desktop=('role', 'button', {'name': 'Dodaj do koszyka'}))
        BTN_GO_TO_CART  = Sel(desktop=('role', 'link',   {'name': 'Przejdź do koszyka'}))

    async def execute(self, instructions: dict) -> ProductData:
        forced = instructions.get('forced_listing_url')
        url = forced if forced else random.choice(self.context.listing_urls)

        # Jeśli URL jest relatywny — złącz z base URL środowiska
        if not url.startswith('http'):
            url = self.context.environment_url.rstrip('/') + url

        self.log(f"Nawiguję do: {url}")
        await self.page.goto(url)
        await self.wait_for_navigation()

        if self.is_desktop:
            await self._hover_before_add()

        name  = await self.get_text(self.Product.NAME)
        price = await self.get_decimal(self.Product.PRICE)

        await self.sloc(self.Actions.BTN_ADD_TO_CART).click()
        await self._after_add_to_cart()

        return ProductData(name=name, price=price, url=url, available=True)

    async def _hover_before_add(self):
        # Hook — tylko desktop, np. hover menu przed dodaniem do koszyka
        pass

    async def _after_add_to_cart(self):
        if await self.is_visible(self.Actions.BTN_GO_TO_CART):
            await self.sloc(self.Actions.BTN_GO_TO_CART).click()
        await self.wait_for_navigation()
