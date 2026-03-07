# Przepływ wykonania (Execution Flow)

Plik opisuje pełną ścieżkę od uruchomienia programu do zapisania alertów w bazie danych.

---

## Diagram ASCII

```
main.py / app/routers/execute.py / app/scheduler.py
    │
    ├─► SuiteExecutor (scenarios/suite_executor.py)
    │       │  asyncio.Semaphore(workers) — równoległość
    │       │
    │       └─► ScenarioExecutor  (scenarios/scenario_executor.py)
    │               │  osobna sesja DB per scenariusz
    │               │
    │               ├─► ScenarioContext.from_db()   ← Scenario + Environment
    │               ├─► Playwright browser launch
    │               ├─► ShopRunner.run()
    │               │       │
    │               │       ├─► HomePage.execute()      → HomeData
    │               │       │       └─► HomeRules.check()     → RulesResult
    │               │       ├─► ListingPage.execute()   → ProductData
    │               │       │       └─► ListingRules.check()  → RulesResult
    │               │       ├─► Cart0Page.execute()     → Cart0Data
    │               │       │       └─► Cart0Rules.check()    → RulesResult
    │               │       ├─► [jeśli is_order:]
    │               │       │   ├─► Cart1Page.execute() → Cart1Data
    │               │       │   │       └─► Cart1Rules.check() → RulesResult
    │               │       │   ├─► Cart2Page.execute() → Cart2Data
    │               │       │   │       └─► Cart2Rules.check() → RulesResult
    │               │       │   ├─► Cart3Page.execute() → Cart3Data
    │               │       │   │       └─► Cart3Rules.check() → RulesResult
    │               │       │   └─► Cart4Page.execute() → Cart4Data
    │               │       │           └─► Cart4Rules.check() → RulesResult
    │               │       └─► GlobalRules.check(run_data) → RulesResult
    │               │
    │               ├─► AlertEngine.add_alert() × N
    │               └─► AlertEngine.save_all() → DB
    │
    └─► SuiteExecutor._finalize_suite_run()
            │  agregacja wyników, AlertGroup deduplication
            └─► DB commit
```

---

## Entry points

### 1. CLI (`main.py`)

```python
python main.py                                      # pierwsza aktywna suite
python main.py --suite 1 --environment 1 --workers 2
python main.py --scenario 5 --environment 1         # pojedynczy scenariusz
python main.py --suite 1 --environment 1 --headless
```

- Parsuje argumenty przez `parse_args()`
- Tworzy sesję DB, ładuje suite/environment/scenarios z bazy
- Tworzy `SuiteExecutor` i wywołuje `executor.run()`
- Na Windows ustawia `WindowsProactorEventLoopPolicy`:

```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.run(run_suite(...))
```

### 2. Panel (`app/routers/execute.py`)

- `POST /execute` → `_start_suite()` → tworzy `SuiteRun` w DB → rejestruje w `RunnerRegistry` → uruchamia `_run_suite_background()` jako asyncio task
- Zwraca redirect do `/suite-runs/{id}` natychmiast (run trwa w tle)

### 3. Scheduler (`app/scheduler.py`)

- APScheduler odpala `tick()` co minutę
- `tick()` sprawdza `ScheduledJob` z `next_run_at <= now` i wywołuje `_start_suite()` z execute.py

---

## SuiteExecutor (`scenarios/suite_executor.py`)

**Rola:** orchestrator całej suite.

1. Tworzy `SuiteRun` (jeśli nie przekazany z zewnątrz) — status `RUNNING`
2. Konfiguruje logging do pliku `logs/suite_run_{id}.log`
3. Tworzy `asyncio.Semaphore(workers)` — kontrola równoległości
4. Dla każdego scenariusza tworzy `run_with_limit(scenario)`:
   - `async with semaphore` — zajmuje slot
   - Tworzy **osobną** sesję DB (`Session(bind=self.db.bind)`)
   - Tworzy `ScenarioExecutor` i wywołuje `executor.run()`
5. `asyncio.gather(*tasks)` — wszystkie scenariusze równolegle
6. `_finalize_suite_run()` — agreguje wyniki i tworzy/aktualizuje `AlertGroup`

### Równoległość

Każdy scenariusz dostaje własną sesję DB (osobny obiekt `Session`), co pozwala na równoczesne zapisy do SQLite dzięki trybowi WAL.

---

## ScenarioExecutor (`scenarios/scenario_executor.py`)

**Rola:** wykonanie jednego scenariusza w przeglądarce.

1. Tworzy `ScenarioContext.from_db(scenario_db, environment_db)`
2. Zapisuje `ScenarioRun` do DB — status `RUNNING`
3. Tworzy `AlertEngine`
4. Uruchamia Playwright Chromium:
   - `headless` wg konfiguracji
   - viewport: `390×844` (mobile) lub `1280×720` (desktop)
5. Tworzy katalog na screenshoty: `screenshots/{suite_run_id}/{scenario_run_id}/`
6. Wywołuje `ShopRunner.run()`
7. Po zakończeniu:
   - `_save_run_data()` — zapisuje `BasketSnapshot` i błędy API
   - `_register_alerts()` → `AlertEngine.add_alert()`
   - `AlertEngine.save_all()`
   - Aktualizuje status `ScenarioRun`: `SUCCESS` / `FAILED` / `CANCELLED`

### Nieoczekiwane zatrzymanie

Jeśli `ShopRunResult.success = False` → ScenarioExecutor rzuca wyjątek → `ScenarioRun.status = FAILED`.

---

## ShopRunner (`scenarios/shop_runner.py`)

**Rola:** orchestrator etapów testu w przeglądarce.

1. Rejestruje listener `page.on('response', _on_response)` — zbiera błędy HTTP >400
2. Pętla retry: `for attempt in range(max_retries + 1)`
3. Wywołuje etapy po kolei (patrz diagram)
4. Po każdym etapie: `_process_result()` — zbiera alerty, akumuluje instructions, rzuca `StopTest` jeśli rules zdecydowały

### `_process_result(result, stage)`

```python
self.alerts.extend(result.alerts)           # zbiera alerty z etapu
self.instructions.update(result.instructions)  # akumuluje instructions
if result.should_stop:
    raise StopTest(stage=stage, reason=result.stop_reason)
```

Instructions są addytywne — każdy etap może dodawać lub nadpisywać klucze.

---

## Retries

- `max_retries` pochodzi z CLI / scheduler / execute form
- Przy błędzie (Exception, nie StopTest): `_reset_for_retry(attempt, forced_listing_url)`
  - Czyści `run_data`, `alerts`, `screenshots`, `api_errors`
  - `_clear_browser_state()` — czyści cookies, localStorage, sessionStorage
  - Jeśli `run_data.listing.url` był znany → zapisuje jako `forced_listing_url` (następny attempt użyje tego samego produktu)
- `StopTest` nie jest retryowany — to intencjonalne zatrzymanie

---

## StopTest

```python
class StopTest(Exception):
    def __init__(self, stage: str, reason: str, expected: bool = True):
        ...
```

| `expected` | Znaczenie | Log poziom |
|---|---|---|
| `True` | Kontrolowane zatrzymanie — flaga `stop_at_cartX`, reguła negatywna | `INFO` |
| `False` | Błąd — dotarł do etapu gdzie nie powinien | `WARNING` |

`ShopRunResult.success` = `e.expected` — decyduje o statusie `ScenarioRun`.

### Flagi powodujące `StopTest(expected=True)`

| Flaga | Etap zatrzymania |
|---|---|
| `stop_at_cart1` | po `Cart1Rules.check()` |
| `stop_at_cart2` | po `Cart2Rules.check()` |
| `stop_at_cart3` | po `Cart3Rules.check()` |
| `should_not_complete` | przed `Cart4Page.execute()` |

---

## Screenshoty

- Katalog: `screenshots/{suite_run_id}/{scenario_run_id}/`
- Plik per etap: `home.png`, `listing.png`, `cart0.png`, `cart1.png`, `cart2.png`, `cart3.png`, `cart4.png`
- Błąd screenshotu nigdy nie przerywa testu (`try/except` z `pass`)
- Ostatni screenshot zapisywany jako `ScenarioRun.screenshot_url`

---

## AlertEngine

Po `ShopRunner.run()`:

1. `_register_alerts(result)` — iteruje `result.alerts` i wywołuje `AlertEngine.add_alert(business_rule, description)`
2. `AlertEngine.add_alert()` — sprawdza `AlertConfig`, dodaje do listy jeśli skonfigurowany
3. `AlertEngine.save_all()` — `db.add_all()` + `db.flush()`

Szczegóły w [ALERT_SYSTEM.md](ALERT_SYSTEM.md).

---

## Windows-specific

Playwright na Windows wymaga `WindowsProactorEventLoopPolicy` gdy uruchamiany z wnętrza działającego event loop (np. z panelu FastAPI):

```python
# main.py
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.run(run_suite_background(...))
```

Bez tego `asyncio.subprocess` (używany przez Playwright) zgłasza błąd na Windows.
