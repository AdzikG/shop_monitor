# Panel webowy (FastAPI + HTMX)

Plik opisuje aplikację FastAPI, wszystkie routery i wzorce używane w panelu.

---

## `app/main.py`

```python
app = FastAPI(title="WACEK - Strażnik TERGsasu", lifespan=lifespan)
```

### Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()   # uruchamia APScheduler
    yield
    scheduler.stop()    # zatrzymuje APScheduler przy shutdown
```

### Static files

| Mount | Katalog | Nazwa |
|---|---|---|
| `/static` | `app/static/` | `static` |
| `/screenshots` | `screenshots/` | `screenshots` |

---

## Routery

| Router | Prefix | Moduł |
|---|---|---|
| auth | `/auth` | `app/routers/auth_router.py` |
| dashboard | `/dashboard` | `app/routers/dashboard.py` |
| suite_runs | `/suite-runs` | `app/routers/suite_runs.py` |
| alerts | `/alerts` | `app/routers/alerts.py` |
| execute | `/execute` | `app/routers/execute.py` |
| scenarios | `/scenarios` | `app/routers/scenarios.py` |
| alert_configs | `/alert-configs` | `app/routers/alert_configs.py` |
| suites | `/suites` | `app/routers/suites.py` |
| dictionaries | `/dictionaries` | `app/routers/dictionaries.py` |
| flags | `/flags` | `app/routers/flags.py` |
| environments | `/environments` | `app/routers/environments.py` |
| config | `/config` | `app/routers/config.py` |
| scheduler | `/scheduler` | `app/routers/scheduler_router.py` |
| api_error_exclusions | `/api-error-exclusions` | `app/routers/api_error_exclusions.py` |

---

## Kluczowe routery

### `/dashboard` (`app/routers/dashboard.py`)

Główny widok statystyk.

| Endpoint | Opis |
|---|---|
| `GET /dashboard` | Pełny dashboard — statystyki, trendy, ostatnie runy |
| `GET /dashboard/runs-table` | HTMX partial — tabela ostatnich runów (auto-refresh) |

**Metryki:**
- Aktywne alerty: `OPEN` + `IN_PROGRESS`
- Backlog: `AWAITING_FIX` + `AWAITING_TEST_UPDATE`
- Nowe dziś: `first_seen_at >= last 24h`
- Scenariusze 24h: count non-cancelled
- Trend: wzrost/spadek alertów tydzień do tygodnia

---

### `/execute` (`app/routers/execute.py`)

Manualne uruchamianie testów.

| Endpoint | Opis |
|---|---|
| `GET /execute` | Formularz uruchamiania |
| `POST /execute` | Uruchom suite (z opcjonalnym override workerów, headless, retries) |
| `POST /execute/manual` | Uruchom listę scenariuszy (z liczbą powtórzeń 1–20) |

#### `_start_suite()` — kluczowa funkcja

```python
async def _start_suite(suite_id, environment_id, workers_override=None,
                        headless=True, triggered_by="manual", max_retries=0):
    # 1. Tworzy SuiteRun w DB (status=RUNNING)
    # 2. Rejestruje task w RunnerRegistry
    # 3. Zwraca suite_run_id natychmiast
    # 4. Task biegnie w tle jako asyncio coroutine
```

#### Kontrola limitów

Przed uruchomieniem sprawdza `runner_registry.count_running() < MAX_CONCURRENT_SUITES`. Jeśli limit osiągnięty → błąd w UI.

---

### `/suite-runs` (`app/routers/suite_runs.py`)

Historia i szczegóły runów.

| Endpoint | Opis |
|---|---|
| `GET /suite-runs` | Lista runów (25 na stronę) |
| `GET /suite-runs/{id}` | Szczegóły suite_run + lista scenario_runs + alert_groups |
| `GET /suite-runs/{id}/logs` | Log tekstowy jako `<pre>` |
| `POST /suite-runs/{id}/cancel` | Anuluj działający run |
| `POST /suite-runs/{id}/delete` | Usuń run z bazy |
| `GET /suite-runs/{suite_id}/{scenario_id}` | Szczegóły scenario_run + alerty + snapshots |

---

### `/alerts` (`app/routers/alerts.py`)

Zarządzanie cyklem życia alertów.

| Endpoint | Opis |
|---|---|
| `GET /alerts` | Lista AlertGroups (filtry: status, environment, search) |
| `GET /alerts/{id}` | Szczegóły AlertGroup + historia + duplikaty |
| `POST /alerts/{id}/assign` | Przypisz do siebie + status IN_PROGRESS |
| `POST /alerts/{id}/resolve` | Zamknij z typem rozwiązania |
| `POST /alerts/{id}/close` | Zamknij z backlogu (fix wdrożony) |

**Filtry listy:**
- `status`: active (OPEN+IN_PROGRESS) / awaiting / closed / all
- `environment_id`: konkretne środowisko lub wszystkie
- `search`: fragment business_rule lub title (case-insensitive)

---

### `/scheduler` (`app/routers/scheduler_router.py`)

CRUD dla zaplanowanych jobów.

| Endpoint | Opis |
|---|---|
| `GET /scheduler` | Lista jobów |
| `POST /scheduler` | Nowy job |
| `POST /scheduler/{id}/toggle` | Włącz/wyłącz |
| `POST /scheduler/{id}/delete` | Usuń |
| `POST /scheduler/{id}/run-now` | Uruchom natychmiast |

---

## RunnerRegistry (`core/runner_registry.py`)

Globalny rejestr aktywnych tasków.

```python
MAX_CONCURRENT_SUITES = 3
_running: dict[int, asyncio.Task]   # suite_run_id → Task
_semaphore: asyncio.Semaphore(3)
```

| Funkcja | Opis |
|---|---|
| `get_running()` | Dict aktywnych runów |
| `is_running(id)` | Boolean |
| `count_running()` | Liczba aktywnych |
| `cancel(id)` | `task.cancel()` |
| `run_suite(id, coro)` | Wrapper z semaphore + cleanup |

`run_suite()` automatycznie usuwa task z `_running` po zakończeniu/błędzie/anulowaniu.

---

## HTMX — wzorzec auto-refresh

Panel używa HTMX do odświeżania tabel bez przeładowania strony.

### Poprawny wzorzec (innerHTML)

```html
<div hx-get="/dashboard/runs-table"
     hx-trigger="load, every 15s"
     hx-swap="innerHTML">
    <!-- zawartość -->
</div>
```

### Dlaczego `innerHTML` a nie `outerHTML`

`outerHTML` zastępuje cały element — HTMX dyrektywy na następnym ticku są tracone (element bez `hx-*` atrybutów). `innerHTML` zastępuje tylko zawartość — element z dyrektywami pozostaje.

---

## Wzorzec formularzy

FastAPI + Jinja2 + redirect 303:

```python
@router.post("/scenarios/{id}/edit")
async def edit_scenario(id: int, name: str = Form(...), db: Session = Depends(get_db)):
    scenario = db.query(Scenario).get(id)
    scenario.name = name
    db.commit()
    return RedirectResponse(url=f"/scenarios/{id}", status_code=303)
```

303 (See Other) — poprawny kod dla POST → GET redirect (przeglądarka wykona GET).

---

## Autentykacja (`app/routers/auth_router.py`)

PIN-based auth z sesją cookie.

- `PANEL_PIN` — zmienna środowiskowa `.env`
- Chronione endpointy sprawdzają sesję przez dependency
- Bez PIN = brak logowania (domyślna instalacja)

---

## Szablony Jinja2

Katalog: `app/templates/`

Każdy router ma swój podkatalog, np.:
- `app/templates/dashboard/`
- `app/templates/suite_runs/`
- `app/templates/alerts/`

Bazowy szablon: `app/templates/base.html` — nawigacja, CSS, HTMX CDN.

---

## Uruchamianie panelu

```bash
python run_panel.py
python run_panel.py --port 8080 --host 0.0.0.0
```

Domyślnie: `http://127.0.0.1:8000`
