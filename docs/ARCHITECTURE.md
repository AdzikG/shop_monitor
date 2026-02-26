# Shop Monitor — Dokumentacja Architektury

## Przegląd Projektu

Shop Monitor to aplikacja do automatycznego testowania procesów e-commerce (koszyk, checkout) z monitoringiem alertów i raportowaniem. System uruchamia scenariusze testowe przez Playwright, agreguje wyniki i prezentuje je w panelu webowym.

---

## Główne Komponenty

```
shop_monitor/
├── app/                    # FastAPI — panel webowy
│   ├── models/            # SQLAlchemy — modele bazy danych
│   ├── routers/           # Endpointy HTTP
│   ├── templates/         # Szablony HTML (Jinja2)
│   └── static/            # CSS/JS (obecnie puste)
├── scenarios/             # Logika uruchamiania testów
├── pages/                 # Page Object Model — interakcje z przeglądarką
├── core/                  # AlertEngine — zbieranie alertów
├── alembic/               # Migracje bazy danych
├── logs/                  # Logi z uruchomień
└── database.py            # Konfiguracja SQLAlchemy
```

---

## Przepływ Danych — Jak Działa System

### 1. Użytkownik Klika "Run" w Panelu

```
Panel (/execute) 
  → POST /execute
    → run_suite_in_thread() [osobny wątek dla Playwright]
      → SuiteExecutor.run()
```

### 2. SuiteExecutor Tworzy Suite Run

```python
# Utworzenie suite_run w bazie
suite_run = SuiteRun(
    suite_id=1,
    environment_id=1,
    status=RUNNING,
    total_scenarios=2
)
db.commit()  # natychmiast — pojawia się w dashboardzie
```

**Suite Run** = jedno uruchomienie całej grupy scenariuszy
- ID, suite, environment, status (running/success/failed/partial)
- Statystyki: total_scenarios, success_scenarios, failed_scenarios, total_alerts
- Timestamps: started_at, finished_at

### 3. Równoległe Uruchamianie Scenariuszy

```python
# Asyncio + Semaphore — kontrola równoległości
semaphore = asyncio.Semaphore(workers=2)

async def run_with_limit(scenario):
    async with semaphore:  # max 2 jednocześnie
        executor = ScenarioExecutor(...)
        return await executor.run()

# Uruchom wszystkie scenariusze
tasks = [run_with_limit(s) for s in scenarios]
results = await asyncio.gather(*tasks)
```

**Semaphore** ogranicza liczbę równoczesnych scenariuszy (workers).

### 4. Pojedynczy Scenariusz — ScenarioExecutor

```python
# Utworzenie scenario_run
run = ScenarioRun(
    suite_run_id=suite_run.id,  # link do suite
    scenario_id=scenario.id,
    status=RUNNING
)
db.commit()

# Playwright — automatyzacja przeglądarki
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=headless)
    page = await browser.new_page()
    
    # Page Object Pattern
    cart_page = CartListPage(page)
    await cart_page.go_to_listing(url)
    product = await cart_page.pick_random_product()
    await cart_page.add_to_cart()
    
    # AlertEngine — zbieranie alertów
    if not product:
        alert_engine.add_alert(
            rule="listing.no_products",
            title="Brak produktów na listingu"
        )
```

**Scenario Run** = jedno uruchomienie pojedynczego scenariusza
- ID, suite_run_id, scenario_id, status
- Wyniki: product_id, product_name, duration
- Relacje: alerts, basket_snapshots, api_errors

### 5. AlertEngine — Zbieranie Alertów

```python
alert_engine = AlertEngine(
    run_id=run.id,
    scenario_id=scenario.id,
    environment_id=environment.id,
    db=db
)

# Nakładanie alertu
alert_engine.add_alert(
    rule="cart.add_to_cart_failed",
    title="Nie udało się dodać do koszyka",
    description="Przycisk niewidoczny",
    alert_type="bug"  # bug/verify/disabled/temp_disabled
)

# Zapis do bazy
alert_engine.save_all()  # zapisuje Alert do bazy
```

**Alert** = pojedynczy alert z jednego scenariusza
- run_id, scenario_id, environment_id
- business_rule (np. "cart.add_to_cart_failed")
- alert_type, title, description
- is_counted (False dla disabled/temp_disabled)

### 6. Agregacja Alertów — AlertGroup

```python
# SuiteExecutor po zakończeniu wszystkich scenariuszy
# grupuje alerty po business_rule

alert_groups = {
    "listing.no_products": {
        'count': 5,
        'scenario_ids': [1, 3, 7, 12, 15]
    }
}

# Zapis do bazy
for rule, data in alert_groups.items():
    AlertGroup(
        suite_run_id=suite_run.id,
        business_rule=rule,
        occurrence_count=5,
        scenario_ids="[1,3,7,12,15]",
        status=OPEN
    )
```

**Alert Group** = zgrupowane alerty w ramach suite run
- suite_run_id, business_rule
- occurrence_count (ile razy wystąpił)
- scenario_ids (lista scenariuszy gdzie wystąpił)
- status (open → in_progress → closed)
- Workflow zarządzany w zakładce Alerts

### 7. Finalizacja Suite Run

```python
# Aktualizacja statusu i statystyk
suite_run.success_scenarios = 15
suite_run.failed_scenarios = 3
suite_run.total_alerts = 12
suite_run.status = PARTIAL  # niektóre failed
suite_run.finished_at = now()
db.commit()
```

**Status Suite Run:**
- `RUNNING` — w trakcie
- `SUCCESS` — wszystkie scenariusze OK
- `FAILED` — wszystkie scenariusze failed
- `PARTIAL` — mix success/failed

---

## Baza Danych — Schemat

### Hierarchia

```
Environment (PRE/RC/PROD)
    ↓
Suite (grupa scenariuszy)
    ↓
SuiteRun (jedno uruchomienie suite)
    ↓
ScenarioRun (jedno uruchomienie scenariusza)
    ↓
Alert (pojedynczy alert)

SuiteRun → AlertGroup (zgrupowane alerty)
```

### Kluczowe Tabele

**environments**
- PRE, RC, PROD
- base_url, login, password

**suites**
- Nazwa grupy scenariuszy (np. "Bez zamówień")
- workers (ile równolegle)

**suite_environments**
- Relacja suite ↔ environment
- cron_expression (harmonogram)
- workers_override (nadpisanie domyślnego)

**scenarios**
- Pojedynczy case testowy
- listing_urls, delivery_name, payment_name, should_order
- Może należeć do wielu suite (przez suite_scenarios)

**suite_scenarios**
- Relacja suite ↔ scenario
- order (kolejność w suite)

**suite_runs**
- Jedno uruchomienie suite
- status, total_scenarios, success/failed, total_alerts
- started_at, finished_at

**scenario_runs**
- Jedno uruchomienie scenariusza
- suite_run_id (link do suite)
- product_id, product_name, status

**alerts**
- Pojedynczy alert
- run_id, scenario_id, environment_id
- business_rule, alert_type, is_counted

**alert_groups**
- Zgrupowane alerty w suite run
- business_rule, occurrence_count, scenario_ids
- status (open/in_progress/closed)

**alert_configs**
- Konfiguracja typu alertu per reguła
- business_rule → alert_type
- disabled_until (dla temp_disabled)

**basket_snapshots**
- Stan koszyka na etapie (list/transport/payment/summary)
- product_price, delivery_price, total_price
- raw_data (pełne dane JSON)

**api_errors**
- Błędy HTTP 4xx/5xx
- endpoint, method, status_code, response_body

### Migracje — Alembic

```bash
# Wygeneruj migrację po zmianie modeli
alembic revision --autogenerate -m "opis zmiany"

# Zastosuj
alembic upgrade head

# Historia
alembic history
```

**WAL Mode** — SQLite działa w trybie Write-Ahead Logging, co pozwala na równoległe zapisy bez blokowania bazy.

---

## Panel Webowy — FastAPI + HTMX

### Routery (app/routers/)

**dashboard.py**
- `GET /dashboard` — główny widok
- `GET /dashboard/runs-table` — HTMX endpoint (auto-refresh co 15s)
- Pokazuje ostatnie 20 suite runs, statystyki

**suite_runs.py**
- `GET /suite-runs` — lista wszystkich suite runs
- `GET /suite-runs/{id}` — szczegóły: scenariusze, alert groups

**alerts.py**
- `GET /alerts?status=active&search=...` — lista alertów z filtrowaniem
- `POST /alerts/{id}/status` — zmiana statusu (open → in_progress → closed)
- Filtry: active (open+in_progress) / closed / all
- Wyszukiwarka: po business_rule lub title

**execute.py**
- `GET /execute` — formularz wyboru suite + environment
- `POST /execute` — uruchamia suite w tle (osobny wątek)

### Szablony (app/templates/)

**base.html**
- Layout z nawigacją
- Dark theme, monospace fonty, brutalny design
- HTMX załadowany

**dashboard.html**
- Statystyki (total runs, failed, alerts)
- Tabela suite runs z auto-refreshem
- `<div hx-get="/dashboard/runs-table" hx-trigger="every 15s">`

**dashboard_runs_table.html**
- Sama tabela (bez outer div z HTMX)
- Podmieniana przez HTMX

**suite_runs_list.html**
- Pełna lista suite runs (ostatnie 100)

**suite_run_detail.html**
- Szczegóły suite run
- Lista alert groups
- Lista scenario runs

**alerts_list.html**
- Filtry (active/closed/all)
- Wyszukiwarka
- Przyciski Start/Close per alert
- Statystyki (ile open/in_progress/closed)

**execute_form.html**
- Wybór suite
- Wybór environment
- Workers override (opcjonalny)
- Checkbox headless

### HTMX Auto-Refresh

```html
<!-- Dashboard odświeża tabelę co 15s -->
<div hx-get="/dashboard/runs-table" 
     hx-trigger="load, every 15s" 
     hx-swap="innerHTML">
    <!-- tabela -->
</div>
```

**Ważne:** `innerHTML` zamiast `outerHTML` — inaczej HTMX traci dyrektywy po pierwszym swap.

---

## Page Object Model — Playwright

### Struktura

```
pages/
├── base_page.py           # Klasa bazowa
└── cart/
    └── cart_0_list.py     # Listing i dodawanie do koszyka
```

### Zasada Separacji

**Page Object** — zbiera dane ze strony, NIE ocenia poprawności
**Business Rule** — weryfikuje dane, NIE dotyka przeglądarki
**Alert Engine** — zapisuje wynik weryfikacji

### Przykład — cart_0_list.py

```python
class CartListPage(BasePage):
    # Selektory jako stałe klasy
    PRODUCT_ITEM = '[data-component-type="s-search-result"]'
    ADD_TO_CART_BUTTON = '#add-to-cart-button'
    
    async def go_to_listing(self, url: str):
        """Przejdź na listing."""
        await self.page.goto(url)
        await self.wait_for_load()
    
    async def pick_random_product(self) -> dict:
        """Wybierz losowy produkt z pierwszych 10."""
        items = await self.page.locator(self.PRODUCT_ITEM).all()
        if not items:
            return None
        product = random.choice(items[:10])
        return {
            'url': await product.get_attribute('href'),
            'name': await product.text_content()
        }
    
    async def add_to_cart(self) -> bool:
        """Dodaj do koszyka. Zwraca True jeśli sukces."""
        button = self.page.locator(self.ADD_TO_CART_BUTTON)
        if await button.is_visible():
            await button.click()
            return True
        return False
```

**BasePage** — metody wspólne:
- `wait_for_load()` — czeka na `domcontentloaded` + 1.5s
- `take_screenshot(name, dir)` — zrzut ekranu
- `get_text(selector)` — pobiera tekst
- `is_visible(selector)` — sprawdza widoczność
- `click(selector)` — klik i czekaj

### Windows + Playwright + Asyncio

**Problem:** Windows nie obsługuje subprocess w domyślnej pętli asyncio.

**Rozwiązanie:** `WindowsProactorEventLoopPolicy` w osobnym wątku.

```python
def run_suite_in_thread(...):
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )
    asyncio.run(run_suite_background(...))
```

---

## Alert System — Workflow

### Typy Alertów

- **bug** — rzeczywisty błąd, liczony
- **verify** — wymaga weryfikacji, liczony
- **disabled** — wyłączony (zmiana biznesowa), NIE liczony
- **temp_disabled** — tymczasowo wyłączony z `disabled_until`, NIE liczony

### Alert Config — Sterowanie Typem

```python
# Tabela alert_configs
business_rule = "calendar.day_unavailable"
alert_type = "temp_disabled"
disabled_until = "2026-03-01"
description = "Zmiana harmonogramu dostaw — weryfikacja w toku"
```

**AlertEngine** sprawdza `alert_configs` przed zapisem:
1. Czy jest konfiguracja dla tej reguły?
2. Jeśli `temp_disabled` — czy `disabled_until` minął?
3. Jeśli tak — zmień na `bug`

### Alert Workflow w Panelu

```
Zakładka Alerts:
  Filtry: Active (open + in_progress) | Closed | All
  Wyszukiwarka: po business_rule lub title
  
Alert Group (jeden wiersz):
  business_rule: "listing.no_products"
  occurrence_count: 5
  scenario_ids: [1, 3, 7, 12, 15]
  status: OPEN
  
Akcje:
  [Start] → zmienia status na IN_PROGRESS
  [Close] → zmienia status na CLOSED
```

**Status:**
- `OPEN` — nowy, nieobsłużony
- `IN_PROGRESS` — ktoś pracuje nad tym
- `CLOSED` — rozwiązany

---

## Skrypty Pomocnicze

**seed.py**
```bash
python seed.py
```
Wypełnia bazę przykładowymi danymi:
- 2 environments (PRE, PROD)
- 1 suite ("Bez zamówień")
- 2 scenariusze (Elektronika - laptop, Książki - Python)
- Powiązania suite ↔ environment ↔ scenario

**clean_runs.py**
```bash
python clean_runs.py
```
Czyści bazę z runów i alertów, zostawia scenariusze/suite/environments.
Pyta o potwierdzenie przed usunięciem.

**main.py** (CLI)
```bash
python main.py --suite 1 --environment 1 --workers 2 --headless
```
Uruchamia suite z linii komend (bez panelu).

**run_panel.py**
```bash
python run_panel.py
python run_panel.py --port 8080
python run_panel.py --host 0.0.0.0  # dostęp z sieci
```
Uruchamia panel webowy.

---

## Co Jest, Czego Nie Ma

### ✅ Zbudowane

- [x] Baza danych SQLAlchemy + Alembic
- [x] Suite runs — agregacja scenariuszy
- [x] Alert groups — grupowanie alertów
- [x] Panel webowy FastAPI + HTMX
- [x] Dashboard z auto-refreshem
- [x] Zakładka Alerts z filtrowaniem i workflow
- [x] Przycisk Run — uruchamianie z panelu
- [x] Równoległość asyncio + Semaphore
- [x] Page Object Model (POC)
- [x] Alert Engine (POC)
- [x] WAL mode dla SQLite (równoległe zapisy)

### ❌ Nie Zbudowane (Punkty Rozwoju)

- [ ] **Scheduler** — APScheduler dla cronów
- [ ] **Prawdziwa logika biznesowa** — przepisanie kalendarzy/gwarancji/dostaw
- [ ] **Business rules** — osobne klasy weryfikacji
- [ ] **Pełny POM** — cart_1_transport, cart_2_payment, cart_3_address, etc.
- [ ] **Porównanie środowisk** — RC vs PROD side-by-side
- [ ] **Szczegóły scenario run** — basket snapshots, API errors
- [ ] **Raporty email** — automatyczne wysyłanie podsumowań
- [ ] **Zarządzanie danymi** — CRUD scenariuszy/suite przez panel
- [ ] **API monitoring** — przechwytywanie błędów HTTP
- [ ] **Video recording** — nagrywanie sesji Playwright
- [ ] **Screenshots** — zrzuty ekranu na każdym etapie

---

## Miejsca do Rozwoju — Gdzie Dodawać Kod

### Nowy Page Object

```
pages/cart/cart_1_transport.py

class CartTransportPage(BasePage):
    async def get_calendar_data(self):
        # Zbiera dane z kalendarza dostaw
        return {
            'available_dates': [...],
            'unavailable_dates': [...]
        }
```

### Nowa Reguła Biznesowa

```
business_rules/calendar_rules.py

class CalendarRules(BaseRule):
    def verify(self, scenario, environment, data, alert_engine):
        # Weryfikuje czy kalendarze są poprawne
        if expected_date not in data['available_dates']:
            alert_engine.add_alert(
                rule="calendar.day_unavailable",
                title="Dzień powinien być dostępny"
            )
```

### Nowy Router

```
app/routers/reports.py

@router.get("/reports")
async def reports_list(...):
    # Pokazuje raporty
```

Dodaj do `app/main.py`:
```python
from app.routers import reports
app.include_router(reports.router)
```

### Nowy Szablon

```
app/templates/reports_list.html

{% extends "base.html" %}
{% block content %}
    <!-- treść -->
{% endblock %}
```

### Nowa Tabela w Bazie

```python
# 1. Dodaj model w app/models/new_table.py
class NewTable(Base):
    __tablename__ = "new_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ...

# 2. Dodaj import w app/models/__init__.py
from app.models.new_table import NewTable

# 3. Wygeneruj migrację
alembic revision --autogenerate -m "add new_table"

# 4. Zastosuj
alembic upgrade head
```

---

## Najważniejsze Koncepty

### 1. Suite Run = Agregacja

Jeden suite run zawiera wiele scenario runs.
Dashboard pokazuje suite runs, NIE pojedyncze scenariusze.

### 2. Alert Groups = Deduplikacja

Zamiast 50 alertów "listing.no_products" w 50 scenariuszach:
→ 1 alert group z `occurrence_count=50` i listą `scenario_ids`

### 3. Separacja Page Object / Business Rule

**Page Object:** `get_calendar_data()` → zwraca dane
**Business Rule:** `verify(data)` → sprawdza poprawność
**Alert Engine:** `add_alert()` → zapisuje wynik

Nigdy nie mieszaj — Page Object NIE wie co jest poprawne.

### 4. Async + Semaphore

```python
semaphore = asyncio.Semaphore(workers)

async def run_scenario():
    async with semaphore:  # czeka jeśli już N scenariuszy działa
        # uruchom scenariusz
```

Kontroluje równoległość bez multiprocessing.

### 5. HTMX Auto-Refresh

```html
<div hx-get="/endpoint" hx-trigger="every 15s" hx-swap="innerHTML">
```

- `every 15s` — odświeżaj co 15 sekund
- `innerHTML` — zamień tylko zawartość (zachowaj dyrektywy HTMX)
- `outerHTML` — zamień cały div (BŁĄD — traci HTMX)

### 6. SQLite WAL Mode

```python
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
```

Pozwala na równoległe zapisy bez `database is locked`.

---

## FAQ

**Q: Dlaczego suite_runs zamiast pokazywać scenario_runs bezpośrednio?**
A: Suite run agreguje 300 scenariuszy w jedno uruchomienie. Dashboard pokazuje 1 wiersz zamiast 300. Kliknięcie rozwija szczegóły.

**Q: Dlaczego alert_groups?**
A: Deduplikacja. Zamiast 50 osobnych alertów → 1 grupa z occurrence_count=50.

**Q: Dlaczego Python zamiast TypeScript?**
A: Lepsze dla logiki biznesowej, data modelingu, Pydantic/pandas. Playwright działa identycznie w obu.

**Q: Dlaczego asyncio zamiast multiprocessing?**
A: Lżejsze, pełna kontrola z panelu, Playwright ma async API, łatwiejsze zbieranie wyników.

**Q: Jak dodać nowe pole do tabeli?**
A: Edytuj model → `alembic revision --autogenerate` → `alembic upgrade head`. Dane zostają.

**Q: Czy mogę uruchamiać scenariusze bez panelu?**
A: Tak, `python main.py --suite 1 --environment 1`.

**Q: Jak zmienić SQLite na MySQL?**
A: Zmień `DATABASE_URL` w `.env` lub `database.py`. Jedna linia. Alembic obsługuje identycznie.

---

## Podsumowanie

System składa się z 3 głównych warstw:

1. **Baza danych** (SQLAlchemy + Alembic)
   - Przechowuje suite runs, scenario runs, alerts, alert groups
   - WAL mode dla równoległych zapisów

2. **Executor** (asyncio + Playwright + POM)
   - Uruchamia scenariusze równolegle
   - Page Objects zbierają dane
   - Alert Engine zapisuje alerty

3. **Panel** (FastAPI + HTMX + Jinja2)
   - Dashboard z auto-refreshem
   - Zakładka Alerts z workflow
   - Przycisk Run

**Kluczowa architektura:**
- Suite Run agreguje Scenario Runs
- Alert Groups deduplikują Alerty
- Page Objects ≠ Business Rules ≠ Alert Engine (separacja)
- Async + Semaphore steruje równoległością
- HTMX odświeża dane bez pełnego reload

**Miejsca rozwoju:**
- Scheduler (APScheduler)
- Prawdziwa logika biznesowa (kalendarz, gwarancje)
- Pełny POM (wszystkie etapy koszyka)
- Porównanie środowisk RC vs PROD
- Raporty email
