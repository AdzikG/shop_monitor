from pages.base_page import BasePage
import logging
import random

logger = logging.getLogger(__name__)


class CartListPage(BasePage):
    """
    Krok 0 koszyka — strona listingu i dodawanie produktu.
    Odpowiada za: losowanie produktu z listingu i dodanie do koszyka.

    Ta klasa TYLKO obsługuje stronę — nie ocenia czy wynik jest poprawny.
    Ocena należy do business_rules.
    """

    # Selektory Amazon.pl — jeden plik, jedna zmiana gdy Amazon zmieni HTML
    PRODUCT_LINKS = "div[data-component-type='s-search-result'] h2 a"
    ADD_TO_CART_BUTTON = "#add-to-cart-button"
    PRODUCT_TITLE = "#productTitle"
    PRODUCT_PRICE = ".a-price .a-offscreen"
    CART_COUNT = "#nav-cart-count"
    POPUP_CLOSE = ".a-popover-closebutton"
    GO_TO_CART_BUTTON = "#hlb-view-cart-trigger, #nav-cart"

    async def go_to_listing(self, url: str):
        """Przechodzi na stronę listingu."""
        logger.info(f"Przechodzę na listing: {url}")
        await self.page.goto(url)
        await self.wait_for_load()

    async def pick_random_product(self) -> dict | None:
        """
        Losuje produkt z listingu.
        Zwraca słownik z danymi produktu lub None jeśli brak produktów.
        """
        try:
            links = self.page.locator(self.PRODUCT_LINKS)
            count = await links.count()

            if count == 0:
                logger.warning("Brak produktów na listingu")
                return None

            # Losuj produkt z pierwszych 10 wyników
            index = random.randint(0, min(count - 1, 9))
            link = links.nth(index)

            product_url = await link.get_attribute("href")
            product_name = (await link.text_content() or "").strip()

            if not product_url:
                return None

            # Uzupełnij URL jeśli jest relatywny
            if product_url.startswith("/"):
                product_url = f"{product_url}"

            logger.info(f"Wylosowany produkt [{index}]: {product_name[:50]}...")
            return {
                "name": product_name,
                "url": product_url,
                "index": index
            }

        except Exception as e:
            logger.error(f"Błąd podczas losowania produktu: {e}")
            return None

    async def go_to_product(self, product_url: str):
        """Przechodzi na stronę produktu."""
        logger.info(f"Przechodzę na produkt: {product_url[:80]}...")
        await self.page.goto(product_url)
        await self.wait_for_load()

    async def get_product_details(self) -> dict:
        """
        Pobiera szczegóły produktu ze strony produktu.
        Zwraca dane — nie ocenia czy są poprawne.
        """
        title = await self.get_text(self.PRODUCT_TITLE)
        price_text = await self.get_text(self.PRODUCT_PRICE)

        # Wyciągnij ID produktu z URL (ASIN dla Amazon)
        current_url = self.page.url
        product_id = None
        if "/dp/" in current_url:
            product_id = current_url.split("/dp/")[1].split("/")[0].split("?")[0]

        return {
            "id": product_id,
            "name": title,
            "price_raw": price_text,
            "url": current_url
        }

    async def add_to_cart(self) -> bool:
        """
        Dodaje produkt do koszyka.
        Zwraca True jeśli się udało, False jeśli nie.
        """
        try:
            button = self.page.locator(self.ADD_TO_CART_BUTTON)
            is_present = await button.is_visible()

            if not is_present:
                logger.warning("Przycisk 'Dodaj do koszyka' nie jest widoczny")
                return False

            await button.click()
            await self.page.wait_for_timeout(2000)

            # Zamknij popup jeśli się pojawił
            if await self.is_visible(self.POPUP_CLOSE):
                await self.page.locator(self.POPUP_CLOSE).click()
                await self.page.wait_for_timeout(500)

            # Sprawdź czy licznik koszyka wzrósł
            cart_count = await self.get_text(self.CART_COUNT)
            success = cart_count is not None and cart_count != "0"

            if success:
                logger.info(f"Produkt dodany do koszyka. Licznik: {cart_count}")
            else:
                logger.warning("Nie udało się potwierdzić dodania do koszyka")

            return success

        except Exception as e:
            logger.error(f"Błąd podczas dodawania do koszyka: {e}")
            return False

    async def get_cart_summary(self) -> dict:
        """
        Pobiera podstawowe dane koszyka po dodaniu produktu.
        Zwraca snapshot stanu koszyka na etapie 'list'.
        """
        cart_count = await self.get_text(self.CART_COUNT)

        return {
            "stage": "list",
            "cart_count": cart_count,
            "add_to_cart_success": cart_count is not None and cart_count != "0"
        }
