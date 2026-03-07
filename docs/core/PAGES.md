# Pages — Page Object Model

Plik opisuje architekturę warstwy pages: `BasePage`, `Sel`, oraz wszystkie konkretne page objects.

---

## BasePage (`scenarios/pages/base_page.py`)

Klasa bazowa dla wszystkich page objects.

```python
class BasePage:
    def __init__(self, page: Page, context: ScenarioContext): ...
```

### Metody lokatorów

| Metoda | Sygnatura | Opis |
|---|---|---|
| `loc(selector)` | `(tuple) → Locator` | Interpretuje tuple selektora, zwraca Playwright Locator |
| `sloc(sel)` | `(Sel) → Locator` | Wybiera wariant desktop/mobile z `Sel`, zwraca Locator |

### Metody pomocnicze

| Metoda | Sygnatura | Opis |
|---|---|---|
| `wait_for_navigation()` | `async → None` | Czeka na `networkidle` |
| `safe_click(selector)` | `async (tuple) → None` | Scrolluje do elementu + click |
| `safe_fill(selector, value)` | `async (tuple, str) → None` | Czyści pole + wypełnia wartością |
| `get_text(selector)` | `async (tuple) → str\|None` | Odczytuje `inner_text()`, strip, None przy błędzie |
| `get_decimal(selector)` | `async (tuple) → float\|None` | Odczytuje tekst, czyści znaki niebędące cyframi, parsuje float |
| `is_visible(selector)` | `async (tuple) → bool` | Sprawdza widoczność, False przy błędzie |
| `log(msg)` | `(str) → None` | Logger z prefiksem klasy |

### Właściwości

| Właściwość | Typ | Opis |
|---|---|---|
| `is_mobile` | `bool` | `context.is_mobile` |
| `is_desktop` | `bool` | `context.is_desktop` |

---

## Sel (`scenarios/pages/base_page.py`)

Dataclass reprezentująca selektor z opcjonalnym wariantem mobilnym.

```python
@dataclass
class Sel:
    desktop: tuple
    mobile: tuple | None = None

    def resolve(self, is_mobile: bool) -> tuple: ...
```

**Użycie:**
```python
BTN_NEXT = Sel(
    desktop=('role', 'button', {'name': 'Dalej'}),
    mobile= ('locator', '.btn-next-mobile'),   # opcjonalne
)
await self.sloc(self.Nav.BTN_NEXT).click()
```

Jeśli `mobile=None` — oba tryby używają `desktop`.

---

## Formaty selektorów w `loc()`

| Typ | Format | Playwright odpowiednik |
|---|---|---|
| `'locator'` | `('locator', 'css_or_xpath')` | `page.locator(...)` |
| `'role'` | `('role', 'button', {'name': 'Dodaj'})` | `page.get_by_role(...)` |
| `'text'` | `('text', 'Kup teraz', {'exact': True})` | `page.get_by_text(...)` |
| `'test_id'` | `('test_id', 'add-to-cart')` | `page.get_by_test_id(...)` |
| `'label'` | `('label', 'Kod pocztowy')` | `page.get_by_label(...)` |
| `'placeholder'` | `('placeholder', 'Wpisz kod...')` | `page.get_by_placeholder(...)` |

---

## Grupowanie selektorów — inner classes

Każdy page grupuje selektory w inner classes tematyczne. Konwencja:

```python
class Cart0Page(BasePage):

    class Cart:            # sekcja: zawartość koszyka
        TOTAL_PRICE = Sel(desktop=('locator', '.cart-total .price'))
        ITEM        = Sel(desktop=('locator', '.cart-item'))
        BTN_NEXT    = Sel(desktop=('role', 'button', {'name': 'Dalej'}))

    class Warranty:        # sekcja: gwarancja
        CHECKBOX = Sel(desktop=('label', 'Gwarancja'))
        BTN_ADD  = Sel(desktop=('role', 'button', {'name': 'Dodaj gwarancję'}))

    class Promo:           # sekcja: kod promocyjny
        FIELD_CODE = Sel(desktop=('placeholder', 'Kod promocyjny'))
```

Zalety: selektory są zgrupowane semantycznie, łatwo znaleźć odpowiedni, można je zastępować w subclassach.

---

## HomePage (`scenarios/pages/home_page.py`)

**Przeznaczenie:** Nawigacja do strony głównej środowiska, akceptacja cookies.

**Zwraca:** `HomeData(loaded=True)`

### Selektory

| Klasa | Selektor | Opis |
|---|---|---|
| `Cookies.BTN_ACCEPT` | `('role', 'button', {'name': 'Akceptuję'})` | Przycisk akceptacji cookies |

### `execute(instructions)` — kroki

1. `page.goto(context.environment_url)` — nawigacja do base URL
2. `wait_for_navigation()` — czeka na networkidle
3. `_accept_cookies()` — klika przycisk jeśli widoczny
4. Jeśli mobile: `_close_app_banner()` (hook — domyślnie `pass`)

### Hooki

| Hook | Opis |
|---|---|
| `_close_app_banner()` | Zamknięcie banera aplikacji mobilnej — nadpisz w subclassie |

---

## ListingPage (`scenarios/pages/listing_page.py`)

**Przeznaczenie:** Nawigacja do strony produktu, dodanie do koszyka.

**Zwraca:** `ProductData(name, price, url, available=True)`

### Selektory

| Klasa | Selektor | Opis |
|---|---|---|
| `Product.NAME` | `('locator', '.product-item .product-name')` | Nazwa produktu |
| `Product.PRICE` | `('locator', '.product-item .product-price')` | Cena produktu |
| `Actions.BTN_ADD_TO_CART` | `('role', 'button', {'name': 'Dodaj do koszyka'})` | Dodaj do koszyka |
| `Actions.BTN_GO_TO_CART` | `('role', 'link', {'name': 'Przejdź do koszyka'})` | Przejdź do koszyka (opcjonalny) |

### `execute(instructions)` — kroki

1. Wybiera URL: `instructions['forced_listing_url']` (retry) lub `random.choice(context.listing_urls)`
2. Jeśli URL relatywny: łączy z `context.environment_url`
3. `page.goto(url)` + `wait_for_navigation()`
4. Desktop: `_hover_before_add()` (hook)
5. Odczytuje nazwę i cenę produktu
6. Klika `BTN_ADD_TO_CART`
7. `_after_add_to_cart()` — jeśli widoczny `BTN_GO_TO_CART`, klika go

### Hooki

| Hook | Opis |
|---|---|
| `_hover_before_add()` | Hover przed dodaniem — tylko desktop (np. hover nad menu) |
| `_after_add_to_cart()` | Po dodaniu — może nawigować do koszyka |

---

## Cart0Page (`scenarios/pages/cart0_page.py`)

**Przeznaczenie:** Podgląd koszyka, opcjonalne dodanie gwarancji/usług, przejście do dostawy.

**Zwraca:** `Cart0Data(total_price, item_count)`

### Selektory

| Klasa | Selektor | Opis |
|---|---|---|
| `Cart.TOTAL_PRICE` | `('locator', '.cart-total .price')` | Łączna cena koszyka |
| `Cart.ITEM` | `('locator', '.cart-item')` | Pozycje w koszyku (count()) |
| `Cart.BTN_NEXT` | `('role', 'button', {'name': 'Dalej'})` | Przejście do dostawy |
| `Warranty.SECTION` | `('locator', '.warranty-section')` | Sekcja gwarancji |
| `Warranty.CHECKBOX` | `('label', 'Gwarancja')` | Checkbox gwarancji |
| `Warranty.BTN_ADD` | `('role', 'button', {'name': 'Dodaj gwarancję'})` | Dodaj gwarancję |
| `Services.SECTION` | `('locator', '.services-section')` | Sekcja usług |
| `Promo.FIELD_CODE` | `('placeholder', 'Kod promocyjny')` | Pole kodu promocyjnego |
| `Promo.BTN_APPLY` | `('role', 'button', {'name': 'Zastosuj'})` | Zastosuj kod |

### `execute(instructions)` — kroki

1. `wait_for_navigation()`
2. Odczytuje `total_price` i liczbę pozycji (`ITEM.count()`)
3. Jeśli `context.is_order`: klika `BTN_NEXT` → przejście do dostawy

---

## Cart1Page (`scenarios/pages/cart1_page.py`)

**Przeznaczenie:** Wybór dostawy, wypełnienie kodu pocztowego.

**Zwraca:** `Cart1Data(available_options, selected, estimated_date, cutoff_time, price, postal_code_required, postal_code_filled)`

### Selektory

| Klasa | Selektor | Opis |
|---|---|---|
| `Delivery.OPTION` | `('locator', '.delivery-option')` | Pojedyncza opcja dostawy |
| `Delivery.NAME` | `('locator', '.delivery-option .name')` | Nazwa opcji |
| `Delivery.ESTIMATED_DATE` | `('locator', '.delivery-option .estimated-date')` | Data szacowanej dostawy |
| `Delivery.CUTOFF_TIME` | `('locator', '.delivery-option .cutoff-time')` | Godzina graniczna |
| `Delivery.PRICE` | `('locator', '.delivery-option .price')` | Cena dostawy |
| `Address.FIELD_POSTAL` | `('placeholder', 'Kod pocztowy')` | Pole kodu pocztowego |
| `Nav.BTN_NEXT` | `('role', 'button', {'name': 'Dalej'})` | Przejście do płatności |

### `execute(instructions)` — fazy

1. **Faza 1**: `_get_available_options()` — zbiera wszystkie nazwy dostaw
2. **Faza 2**: `_select_delivery()` — klika w opcję zgodną z `context.delivery_name`
3. **Faza 3**: `_handle_post_selection()` — reaguje na to co pojawiło się po wyborze:
   - Sprawdza czy `FIELD_POSTAL` jest widoczne
   - Jeśli tak i mamy `context.postal_code`: wypełnia pole
   - Desktop hook: `_handle_desktop_post_selection()`
4. **Faza 4**: odczytuje `date`, `cutoff`, `price`
5. Jeśli `is_order` i dostawa wybrana: klika `BTN_NEXT`

### Hooki

| Hook | Opis |
|---|---|
| `_handle_desktop_post_selection()` | Po wyborze dostawy na desktop (np. popup potwierdzenia) |

---

## Cart2Page (`scenarios/pages/cart2_page.py`)

**Przeznaczenie:** Wybór metody płatności.

**Zwraca:** `Cart2Data(available_options, selected, price)`

### Selektory — konwencja analogiczna do Cart1Page

Klasy: `Payment`, `Nav`.

### `execute(instructions)` — kroki

1. Zbiera dostępne opcje płatności
2. Klika w opcję zgodną z `context.payment_name`
3. Odczytuje cenę wybranej płatności
4. Jeśli `is_order`: klika `BTN_NEXT`

---

## Cart3Page (`scenarios/pages/cart3_page.py`)

**Przeznaczenie:** Formularz adresowy.

**Zwraca:** `Cart3Data(postal_code, street, city, is_company)`

### `execute(instructions)` — kroki

1. Wypełnia dane adresowe (imię, nazwisko, telefon, email, ulica, kod, miasto)
2. Jeśli `instructions.get('fill_company_fields')`: dodaje dane firmowe
3. Jeśli `is_order`: klika `BTN_NEXT`

---

## Cart4Page (`scenarios/pages/cart4_page.py`)

**Przeznaczenie:** Podsumowanie zamówienia, opcjonalne złożenie zamówienia.

**Zwraca:** `Cart4Data(total_price, delivery_name, delivery_price, payment_name, order_number)`

### Selektory

| Klasa | Selektor | Opis |
|---|---|---|
| `Summary.TOTAL_PRICE` | `('locator', '.summary-total .price')` | Łączna cena w podsumowaniu |
| `Summary.DELIVERY_NAME` | `('locator', '.summary-delivery .name')` | Nazwa dostawy |
| `Summary.DELIVERY_PRICE` | `('locator', '.summary-delivery .price')` | Cena dostawy |
| `Summary.PAYMENT_NAME` | `('locator', '.summary-payment .name')` | Nazwa płatności |
| `Confirmation.ORDER_NUMBER` | `('locator', '.order-confirmation .order-number')` | Numer zamówienia |
| `Nav.BTN_ORDER` | `('role', 'button', {'name': 'Zamawiam i płacę'})` | Złóż zamówienie |

### `execute(instructions)` — kroki

1. Odczytuje dane z podsumowania (cena, dostawa, płatność)
2. Jeśli `context.is_order`:
   - `_before_order()` (hook)
   - Klika `BTN_ORDER`
   - Odczytuje `order_number`

### Hooki

| Hook | Opis |
|---|---|
| `_before_order()` | Przed kliknięciem "Zamawiam" — np. akceptacja regulaminu |

---

## Jak dodać nowy page

Szczegółowy checklist w [HOW_TO_EXTEND.md](HOW_TO_EXTEND.md).

Skrót:
1. `scenarios/pages/newstage_page.py` — klasa dziedzicząca `BasePage`
2. Grupuj selektory w inner classes
3. Zaimplementuj `async execute(instructions: dict) -> NewStageData`
4. Eksportuj z `scenarios/pages/__init__.py`
5. Dodaj odpowiednie Rules w `scenarios/rules/`
6. Dodaj etap do `ShopRunner.run()` i `RunData`
