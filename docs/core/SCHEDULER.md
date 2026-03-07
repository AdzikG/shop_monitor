# Scheduler — automatyczne uruchamianie suite

Plik opisuje mechanizm cron-schedulera opartego na APScheduler i croniter.

---

## Architektura

- **APScheduler** (`AsyncIOScheduler`) — wbudowany timer co minutę
- **croniter** — parsowanie wyrażeń cron i obliczanie następnego uruchomienia
- **ScheduledJob** — rekord DB definiujący kiedy i co uruchomić

Scheduler działa w ramach aplikacji FastAPI — uruchamiany w `lifespan` (`app/main.py`).

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()    # start przy uruchomieniu FastAPI
    yield
    scheduler.stop()     # stop przy zamknięciu
```

---

## `start()` i `stop()` (`app/scheduler.py`)

```python
def start():
    scheduler.add_job(tick, "interval", minutes=1, id="scheduler_tick", replace_existing=True)
    scheduler.start()

def stop():
    scheduler.shutdown(wait=False)
```

`replace_existing=True` — bezpieczne przy hot-reloadzie (zastępuje istniejące zadanie).

---

## `tick()` — główna pętla

Wywoływana co minutę przez APScheduler.

```python
async def tick():
    now = datetime.now(timezone.utc)
    jobs = db.query(ScheduledJob).filter(
        ScheduledJob.is_enabled == True,
        ScheduledJob.next_run_at <= now,
    ).all()

    for job in jobs:
        suite_run_id = await _start_suite(...)
        job.last_run_at = now
        job.last_suite_run_id = suite_run_id
        job.next_run_at = _next_run(job.cron)  # zawsze, nawet przy błędzie

    db.commit()
```

**Ważne:** `next_run_at` jest zawsze aktualizowane — nawet jeśli uruchomienie się nie powiodło. Dzięki temu scheduler nie blokuje się na pętli błędów.

`_start_suite` importowany wewnątrz `tick()` (unikanie circular import):
```python
from app.routers.execute import _start_suite
```

---

## `_next_run(cron)` i `compute_next_run(cron)`

```python
def _next_run(cron: str) -> datetime:
    now = datetime.now(timezone.utc)
    cron_iter = croniter(cron, now)
    return cron_iter.get_next(datetime).replace(tzinfo=timezone.utc)

def compute_next_run(cron: str) -> datetime | None:
    try:
        return _next_run(cron)
    except Exception:
        return None  # nieprawidłowy cron
```

`compute_next_run()` — publiczne API używane przez router schedulera do walidacji cron przed zapisem.

---

## Format wyrażeń cron

Standard 5-polowy cron:

```
┌───────── minuta (0-59)
│ ┌─────── godzina (0-23)
│ │ ┌───── dzień miesiąca (1-31)
│ │ │ ┌─── miesiąc (1-12)
│ │ │ │ ┌─ dzień tygodnia (0-7, 0 i 7 = niedziela)
│ │ │ │ │
* * * * *
```

### Przykłady

| Cron | Kiedy |
|---|---|
| `0 8 * * 1-5` | Każdy dzień roboczy o 08:00 UTC |
| `30 6 * * *` | Każdy dzień o 06:30 UTC |
| `0 */2 * * *` | Co 2 godziny |
| `0 9,17 * * 1-5` | Dni robocze o 09:00 i 17:00 UTC |
| `0 8 * * 1` | Każdy poniedziałek o 08:00 UTC |

Walidacja przez `croniter` — wyjątek przy nieprawidłowym wyrażeniu.

---

## ScheduledJob — model

| Pole | Typ | Opis |
|---|---|---|
| `suite_id` | FK → Suite | Która suite uruchamiać |
| `environment_id` | FK → Environment | Na jakim środowisku |
| `workers` | int | Liczba równoległych workerów |
| `max_retries` | int (default: 0) | Liczba ponownych prób przy błędzie scenariusza |
| `cron` | str | Wyrażenie cron |
| `is_enabled` | bool | Czy job jest aktywny |
| `next_run_at` | datetime\|None | Kiedy następne uruchomienie |
| `last_run_at` | datetime\|None | Kiedy ostatnie uruchomienie |
| `last_suite_run_id` | FK → SuiteRun\|None | Ostatni wynik |

---

## Router schedulera (`app/routers/scheduler_router.py`)

| Endpoint | Akcja |
|---|---|
| `GET /scheduler` | Lista wszystkich jobów + formularze |
| `POST /scheduler` | Utwórz nowy job |
| `POST /scheduler/{id}/toggle` | Włącz/wyłącz job |
| `POST /scheduler/{id}/delete` | Usuń job |
| `POST /scheduler/{id}/run-now` | Uruchom natychmiast |

### Tworzenie joba

1. Walidacja cron przez `compute_next_run()` — błędny cron → error bez zapisu
2. `is_enabled = True`, `next_run_at` = wynik `compute_next_run()`
3. Zapis do DB

### Toggle (włącz/wyłącz)

- Wyłączenie: `is_enabled = False`
- Włączenie: `is_enabled = True` + przeliczenie `next_run_at` (żeby nie było w przeszłości)

### Run-now

Wywołuje `_start_suite()` z parametrami joba (te same co scheduler). Aktualizuje `last_run_at` i `last_suite_run_id`.

---

## Logi schedulera

Osobny plik log dla schedulera:

```
logs/scheduler_YYYY-MM-DD.log
```

Format: `HH:MM:SS | LEVEL    | Wiadomość`

Logi APScheduler (wewnętrzne) kierowane do tego samego pliku.

---

## Uwagi

- Scheduler używa UTC — zapewnij że `next_run_at` w DB jest zawsze w UTC
- APScheduler nie gwarantuje dokładności do sekundy — tick co minutę = tolerancja ~1 min
- Jednoczesne uruchomienie tego samego joba dwa razy jest niemożliwe (tick sprawdza `next_run_at <= now` i natychmiast aktualizuje)
