import random
from scenarios.pages.base_page import BasePage
from scenarios.run_data import ProductData

# ── ListingPage ───────────────────────────────────────────────────────────────

class ListingPage(BasePage):
    PRODUCT_NAME  = ('locator', '.product-item .product-name')
    PRODUCT_PRICE = ('locator', '.product-item .product-price')
    ADD_TO_CART   = ('role', 'button', {'name': 'Dodaj do koszyka'})
    GO_TO_CART    = ('role', 'link', {'name': 'Przejdź do koszyka'})

    async def execute(self, instructions: dict) -> ProductData:
        url = random.choice(self.context.listing_urls)
        self.log(f"Nawiguję do: {url}")
        await self.page.goto(url)
        await self.wait_for_navigation()

        if self.is_desktop:
            await self._hover_before_add()

        name  = await self.get_text(self.PRODUCT_NAME)
        price = await self.get_decimal(self.PRODUCT_PRICE)

        await self.loc(self.ADD_TO_CART).click()
        await self._after_add_to_cart()

        return ProductData(name=name, price=price, url=url, available=True)

    async def _hover_before_add(self):
        # Hook — tylko desktop, np. hover menu
        pass

    async def _after_add_to_cart(self):
        if await self.is_visible(self.GO_TO_CART):
            await self.loc(self.GO_TO_CART).click()
        await self.wait_for_navigation()