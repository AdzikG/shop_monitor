# ScenarioContext i RunData

Plik opisuje dwa kluczowe obiekty danych przepływające przez cały test: `ScenarioContext` (konfiguracja tylko do odczytu) i `RunData` (akumulowane fakty).

---

## ScenarioContext (`scenarios/context.py`)

Niemutowalny (read-only) kontener konfiguracji dla jednego przebiegu testu. Budowany z rekordów DB przez `from_db()`.

```python
@dataclass
class ScenarioContext:
    scenario_id: int
    scenario_name: str
    environment_url: str
    environment_name: str
    listing_urls: list[str]
    delivery_name: Optional[str] = None
    delivery_cutoff: Optional[str] = None
    payment_name: Optional[str] = None
    basket_type: Optional[str] = None
    postal_code: Optional[str] = None
    guarantee: bool = False
    is_order: bool = False
    services: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
```

### Pola z typami i źródłem

| Pole | Typ | Źródło w DB | Opis |
|---|---|---|---|
| `scenario_id` | `int` | `Scenario.id` | ID scenariusza |
| `scenario_name` | `str` | `Scenario.name` | Nazwa scenariusza |
| `environment_url` | `str` | `Environment.base_url` | Base URL środowiska |
| `environment_name` | `str` | `Environment.name` | Nazwa środowiska |
| `listing_urls` | `list[str]` | `Scenario.listing_urls` (JSON) | Lista URL-i produktów (losowy wybór) |
| `delivery_name` | `str\|None` | `Scenario.delivery_name` | Oczekiwana metoda dostawy |
| `delivery_cutoff` | `str\|None` | `Scenario.delivery_cutoff` | Oczekiwana godzina graniczna |
| `payment_name` | `str\|None` | `Scenario.payment_name` | Oczekiwana metoda płatności |
| `basket_type` | `str\|None` | `Scenario.basket_type` | Typ koszyka (np. "standardowy") |
| `postal_code` | `str\|None` | `Scenario.postal_code` | Kod pocztowy do formularza |
| `guarantee` | `bool` | `Scenario.guarantee` | Czy dodawać gwarancję |
| `is_order` | `bool` | `Scenario.is_order` | Czy przejść przez cały checkout |
| `services` | `list[str]` | `Scenario.services` (JSON str) | Lista usług do dodania |
| `flags` | `dict[str, bool]` | `ScenarioFlag` join table | Flagi sterujące zachowaniem |

### Metody i właściwości

#### `flag(name: str, default: bool = False) → bool`

Zwraca wartość flagi z `self.flags` lub `default` jeśli flaga nie istnieje.

```python
context.flag('mobile')          # → True/False
context.flag('stop_at_cart1')   # → True/False
context.flag('nonexistent')     # → False (default)
```

#### `is_mobile → bool`

`self.flag('mobile')` — True jeśli scenariusz testuje widok mobilny.

#### `is_desktop → bool`

`not self.flag('mobile')` — True dla widoku desktop.

### `from_db(scenario, environment) → ScenarioContext`

Fabryka tworząca `ScenarioContext` z obiektów SQLAlchemy.

```python
context = ScenarioContext.from_db(scenario_db, environment_db)
```

Kroki:
1. Parsuje `scenario.services` (JSON string → `list[str]`)
2. Buduje `flags`: `{sf.flag.name: sf.is_enabled for sf in scenario.flags}`
3. Konstruuje i zwraca `ScenarioContext`

---

## Przepływ danych ScenarioContext

```
DB: Scenario + Environment
       │
       ▼
ScenarioContext.from_db()
       │
       ├─► ShopRunner(context=...)
       │       │
       │       ├─► Page.__init__(context=context)    — dostępny w każdym page
       │       └─► Rules.__init__(context=context)   — dostępny w każdych rules
       │
       └─► ScenarioExecutor (context tworzony wewnętrznie)
```

---

## Flagi — ważne przykłady

| Flaga | Typ | Efekt |
|---|---|---|
| `mobile` | bool | viewport 390×844, `is_mobile=True` |
| `stop_at_cart1` | bool | `StopTest` po Cart1Rules |
| `stop_at_cart2` | bool | `StopTest` po Cart2Rules |
| `stop_at_cart3` | bool | `StopTest` po Cart3Rules |
| `should_not_complete` | bool | `StopTest(expected=False)` przed Cart4 |
| `company_address` | bool | Cart0Rules dodaje `fill_company_fields` do instructions |

Flagi zarządzane przez panel (`/flags`). `FlagDefinition` definiuje dostępne flagi globalnie, `ScenarioFlag` przypisuje wartość per scenariusz.

---

## RunData (`scenarios/run_data.py`)

Akumulator faktów zebranych przez Pages podczas przebiegu testu. Przekazywany do Rules po każdym etapie.

```python
@dataclass
class RunData:
    home:    Optional[HomeData]    = None
    listing: Optional[ProductData] = None
    cart0:   Optional[Cart0Data]   = None
    cart1:   Optional[Cart1Data]   = None
    cart2:   Optional[Cart2Data]   = None
    cart3:   Optional[Cart3Data]   = None
    cart4:   Optional[Cart4Data]   = None
```

Pole jest `None` jeśli etap nie był wykonywany (np. `cart1`–`cart4` przy `is_order=False`).

---

## Data classy

### `HomeData`

```python
@dataclass
class HomeData:
    loaded: bool = False
```

| Pole | Opis |
|---|---|
| `loaded` | True = strona główna załadowała się |

**Fakt zbierany przez:** `HomePage.execute()`
**Oceniany przez:** `HomeRules` — `not loaded` → stop

---

### `ProductData`

```python
@dataclass
class ProductData:
    name: Optional[str] = None
    price: Optional[float] = None
    url: Optional[str] = None
    available: bool = True
```

| Pole | Opis |
|---|---|
| `name` | Nazwa produktu z listingu |
| `price` | Cena produktu z listingu |
| `url` | URL produktu (ważne przy retry) |
| `available` | True = produkt dostępny |

**Fakt zbierany przez:** `ListingPage.execute()`
**Oceniany przez:** `ListingRules` + `GlobalRules` (porównanie ceny listing vs koszyk)

---

### `Cart0Data`

```python
@dataclass
class Cart0Data:
    total_price: Optional[float] = None
    item_count: int = 0
    products: list[ProductData] = field(default_factory=list)
```

| Pole | Opis |
|---|---|
| `total_price` | Łączna cena w koszyku (przed dostawą) |
| `item_count` | Liczba pozycji w koszyku |
| `products` | Lista produktów (opcjonalne) |

**Fakt zbierany przez:** `Cart0Page.execute()`
**Oceniany przez:** `Cart0Rules` (pusty koszyk, brak ceny) + `Cart4Rules` (porównanie cen)

---

### `Cart1Data`

```python
@dataclass
class Cart1Data:
    available_options: list[str] = field(default_factory=list)
    selected: Optional[str] = None
    estimated_date: Optional[str] = None
    cutoff_time: Optional[str] = None
    price: Optional[float] = None
    postal_code_required: bool = False
    postal_code_filled: bool = False
```

| Pole | Opis |
|---|---|
| `available_options` | Wszystkie opcje dostawy widoczne na stronie |
| `selected` | Nazwa wybranej dostawy (None = nie wybrano) |
| `estimated_date` | Szacowana data dostawy |
| `cutoff_time` | Godzina graniczna zamówienia |
| `price` | Cena wybranej dostawy |
| `postal_code_required` | Page widział pole kodu pocztowego |
| `postal_code_filled` | Page wypełnił pole kodu pocztowego |

**Fakt zbierany przez:** `Cart1Page.execute()`
`postal_code_required/filled` to "fakty" — page nie ocenia czy to błąd, rules decydują.

---

### `Cart2Data`

```python
@dataclass
class Cart2Data:
    available_options: list[str] = field(default_factory=list)
    selected: Optional[str] = None
    price: Optional[float] = None
```

**Fakt zbierany przez:** `Cart2Page.execute()`
**Oceniany przez:** `Cart2Rules` (brak płatności, nie można wybrać)

---

### `Cart3Data`

```python
@dataclass
class Cart3Data:
    postal_code: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    is_company: bool = False
```

**Fakt zbierany przez:** `Cart3Page.execute()`
**Oceniany przez:** `Cart3Rules` (niezgodność kodu pocztowego)

---

### `Cart4Data`

```python
@dataclass
class Cart4Data:
    total_price: Optional[float] = None
    delivery_name: Optional[str] = None
    delivery_price: Optional[float] = None
    payment_name: Optional[str] = None
    order_number: Optional[str] = None
```

| Pole | Opis |
|---|---|
| `total_price` | Łączna cena w podsumowaniu |
| `delivery_name` | Nazwa dostawy z podsumowania |
| `delivery_price` | Cena dostawy z podsumowania |
| `payment_name` | Nazwa płatności z podsumowania |
| `order_number` | Numer zamówienia (po kliknięciu "Zamawiam") |

**Fakt zbierany przez:** `Cart4Page.execute()`
**Oceniany przez:** `Cart4Rules` (rozbieżności cen, dostawy, płatności)

---

## Przepływ danych RunData

```
ShopRunner.run_data = RunData()

_run_home()    → run_data.home    = HomeData(...)
HomeRules.check(run_data)         # widzi: run_data.home

_run_listing() → run_data.listing = ProductData(...)
ListingRules.check(run_data)      # widzi: run_data.home, run_data.listing

_run_cart0()   → run_data.cart0   = Cart0Data(...)
Cart0Rules.check(run_data)        # widzi: ..., run_data.cart0

_run_cart1()   → run_data.cart1   = Cart1Data(...)
Cart1Rules.check(run_data)        # widzi: ..., run_data.cart1

...

GlobalRules.check(run_data)       # widzi WSZYSTKIE pola
```

Rules każdego etapu mają dostęp do danych ze WSZYSTKICH poprzednich etapów.
