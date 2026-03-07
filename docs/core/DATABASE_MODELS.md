# Modele bazy danych

Plik opisuje wszystkie modele SQLAlchemy, ich pola, relacje i przeznaczenie.

---

## Diagram hierarchii

```
Suite ──────────────────────────────────────────────────────────┐
  │                                                             │
  ├──[SuiteScenario]── Scenario                               ScheduledJob
  │         (M:N z kolejnością)    │
  │                                ├── ScenarioFlag ── FlagDefinition
  └── SuiteRun                     └── ScenarioRun
        │                                │
        ├── AlertGroup                   ├── Alert
        │     (deduplikacja)             ├── BasketSnapshot
        └── Environment                 └── ApiError
```

---

## Suite (`app/models/suite.py`)

Kontener grupujący scenariusze w zestaw testów.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `name` | str (unique) | Nazwa zestawu |
| `description` | str\|None | Opis |
| `workers` | int (default: 6) | Domyślna liczba równoległych workerów |
| `is_active` | bool | Czy suite jest aktywna |
| `created_at` | datetime UTC | |
| `updated_at` | datetime UTC | |

**Relacje:**
- `suite_scenarios` → `SuiteScenario` (1:N, cascade delete)
- `suite_runs` → `SuiteRun` (1:N)
- `scheduled_jobs` → `ScheduledJob` (1:N, cascade delete)

---

## Scenario (`app/models/scenario.py`)

Konfiguracja pojedynczego scenariusza testowego.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `name` | str | Nazwa scenariusza |
| `description` | str\|None | Opis |
| `is_active` | bool | Czy scenariusz jest aktywny |
| `listing_urls` | JSON list | URL-e produktów (wybierany losowo) |
| `delivery_name` | str\|None | Oczekiwana metoda dostawy |
| `delivery_cutoff` | str\|None | Oczekiwana godzina graniczna |
| `payment_name` | str\|None | Oczekiwana metoda płatności |
| `basket_type` | str\|None | Typ koszyka |
| `services` | str\|None | JSON string z listą usług |
| `postal_code` | str\|None | Kod pocztowy do formularza adresowego |
| `is_order` | bool | True = przechodzi przez pełny checkout (Cart1–Cart4) |
| `guarantee` | bool | Czy dodawać gwarancję |
| `created_at` | datetime UTC | |
| `updated_at` | datetime UTC | |

**Relacje:**
- `suite_scenarios` → `SuiteScenario` (M:N)
- `runs` → `ScenarioRun` (1:N)
- `flags` → `ScenarioFlag` (1:N, cascade delete)

**Metody:**
- `get_services() → list` — parsuje JSON `services`
- `get_flags_dict() → dict[str, bool]` — zwraca `{flag_name: is_enabled}`

---

## SuiteScenario (`app/models/suite_scenario.py`)

Tabela łącząca Suite ↔ Scenario z kolejnością i stanem aktywności.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `suite_id` | FK → Suite | |
| `scenario_id` | FK → Scenario | |
| `order` | int | Kolejność w ramach suite |
| `is_active` | bool | Czy para jest aktywna |

**Relacje:**
- `suite` → `Suite`
- `scenario` → `Scenario`

---

## Environment (`app/models/environment.py`)

Środowisko testowe (PRE, RC, PROD, Custom).

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `name` | str | Nazwa środowiska |
| `base_url` | str | Base URL (np. `https://www.sklep.pl`) |
| `type` | str | Typ (np. "production", "staging") |
| `is_active` | bool | |
| `created_at` | datetime UTC | |

**Relacje:**
- `runs` → `ScenarioRun` (1:N)
- `suite_runs` → `SuiteRun` (1:N)
- `scheduled_jobs` → `ScheduledJob` (1:N)

---

## SuiteRun (`app/models/suite_run.py`)

Jedno wykonanie całej suite.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `suite_id` | FK → Suite | |
| `environment_id` | FK → Environment | |
| `status` | Enum | RUNNING / SUCCESS / FAILED / PARTIAL / CANCELLED |
| `started_at` | datetime UTC | |
| `finished_at` | datetime UTC\|None | |
| `triggered_by` | str | "manual" lub "scheduler" |
| `total_scenarios` | int | Łączna liczba scenariuszy |
| `success_scenarios` | int | Liczba zakończonych sukcesem |
| `failed_scenarios` | int | Liczba zakończonych błędem |
| `total_alerts` | int | Łączna liczba alertów |

**Relacje:**
- `suite` → `Suite`
- `environment` → `Environment`
- `scenario_runs` → `ScenarioRun` (1:N, cascade delete)
- `alert_groups` → `AlertGroup` (back-populates przez `last_suite_run_id`)

**Właściwości:**
- `duration_seconds` — obliczane z `finished_at - started_at`

**Statusy:**

| Status | Opis |
|---|---|
| RUNNING | W trakcie |
| SUCCESS | Wszystkie scenariusze zakończone sukcesem |
| FAILED | Wszystkie zakończone błędem |
| PARTIAL | Część sukcesów, część błędów |
| CANCELLED | Anulowane przez użytkownika |

---

## ScenarioRun (`app/models/run.py`)

Jedno wykonanie jednego scenariusza w ramach suite_run.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `suite_run_id` | FK → SuiteRun | |
| `scenario_id` | FK → Scenario | |
| `suite_id` | FK → Suite | |
| `environment_id` | FK → Environment | |
| `status` | Enum | RUNNING / SUCCESS / FAILED / SKIPPED / CANCELLED |
| `started_at` | datetime UTC | |
| `finished_at` | datetime UTC\|None | |
| `product_name` | str\|None | Nazwa produktu (z `ProductData.name`) |
| `screenshot_url` | str\|None | Ścieżka do ostatniego screenshotu |
| `video_url` | str\|None | Ścieżka do nagrania (jeśli włączone) |

**Relacje:**
- `suite_run` → `SuiteRun`
- `scenario` → `Scenario`
- `alerts` → `Alert` (1:N, cascade delete)
- `basket_snapshots` → `BasketSnapshot` (1:N, cascade delete)
- `api_errors` → `ApiError` (1:N, cascade delete)

**Właściwości:**
- `duration_seconds` — obliczane z `finished_at - started_at`

---

## Alert (`app/models/alert.py`)

Pojedynczy alert wygenerowany podczas wykonywania scenariusza.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `run_id` | FK → ScenarioRun | |
| `scenario_id` | FK → Scenario | |
| `environment_id` | FK → Environment | |
| `alert_type` | str | Slug AlertType (snapshot) |
| `title` | str | Tytuł (snapshot z AlertConfig.name) |
| `description` | str\|None | Opis szczegółowy |
| `business_rule` | str | Identyfikator reguły |
| `is_counted` | bool (default: True) | Czy wliczany do statystyk |
| `created_at` | datetime UTC | |

**Uwaga:** `Alert` to raw rekord — deduplication odbywa się przez `AlertGroup`.

---

## AlertConfig (`app/models/alert_config.py`)

Konfiguracja gating alertów. Jeden rekord na jeden `business_rule`.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `business_rule` | str (UNIQUE) | Identyfikator reguły |
| `name` | str | Tytuł alertu w UI |
| `alert_type_id` | FK → AlertType | |
| `description` | str\|None | Opis dla developerów |
| `is_active` | bool | False = alert cicho ignorowany |
| `disabled_from_date` | date\|None | Okno wyłączenia — data od |
| `disabled_to_date` | date\|None | Okno wyłączenia — data do |
| `disabled_from_time` | time\|None | Okno wyłączenia — czas od |
| `disabled_to_time` | time\|None | Okno wyłączenia — czas do |
| `updated_by` | str\|None | Kto ostatnio zmienił |

**Metody:**
- `is_disabled_now() → bool` — sprawdza harmonogram wyłączenia

---

## AlertType (`app/models/alert_type.py`)

Kategoria alertu. Seeded przez `seed_alert_types.py`.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `name` | str (unique) | Pełna nazwa |
| `slug` | str (unique) | Identyfikator: bug/to_verify/to_improve/disabled |
| `color` | str | Kolor hex |
| `description` | str | Opis |
| `is_active` | bool | |

---

## AlertGroup (`app/models/alert_group.py`)

Deduplikator i tracker cyklu życia problemu.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `last_suite_run_id` | FK → SuiteRun | Ostatni run z tym alertem |
| `suite_run_history` | JSON str (list) | Lista ID wszystkich suite_runów |
| `business_rule` | str | Identyfikator reguły |
| `alert_type` | str | Slug (snapshot) |
| `title` | str | Tytuł (snapshot) |
| `occurrence_count` | int | Wystąpienia w ostatnim runie |
| `scenario_ids` | JSON str (list) | Posortowane ID scenariuszy |
| `repeat_count` | int | Łączna liczba runów z tym alertem |
| `clean_runs_count` | int | Runów bez alertu od ostatniego wystąpienia |
| `status` | Enum | OPEN/IN_PROGRESS/AWAITING_FIX/AWAITING_TEST_UPDATE/CLOSED |
| `resolution_type` | str\|None | bug/needs_dev/config/script_fix/scenario_fix/nab/duplicate/cant_reproduce |
| `resolution_note` | str\|None | Notatka przy rozwiązaniu |
| `resolved_at` | datetime\|None | Kiedy zamknięto |
| `duplicate_of_id` | FK (self)\|None | Nadrzędny AlertGroup jeśli DUPLICATE |
| `assigned_to` | str\|None | Przypisany do osoby |
| `assigned_at` | datetime\|None | |
| `first_seen_at` | datetime | Pierwsze wystąpienie |
| `last_seen_at` | datetime | Ostatnie wystąpienie |

---

## ScheduledJob (`app/models/scheduled_job.py`)

Zadanie cron — automatyczne uruchamianie suite.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `suite_id` | FK → Suite | |
| `environment_id` | FK → Environment | |
| `workers` | int | Liczba równoległych workerów |
| `max_retries` | int (default: 0) | Liczba ponownych prób przy błędzie |
| `cron` | str | Wyrażenie cron (np. "0 8 * * 1-5") |
| `is_enabled` | bool | |
| `next_run_at` | datetime\|None | Kiedy kolejne uruchomienie |
| `last_run_at` | datetime\|None | Kiedy ostatnie uruchomienie |
| `last_suite_run_id` | FK → SuiteRun\|None | Ostatni wynik |
| `created_at` | datetime UTC | |
| `updated_at` | datetime UTC | |

---

## FlagDefinition (`app/models/flag_definition.py`)

Globalna definicja flagi sterującej zachowaniem scenariuszy.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `name` | str (unique) | Identyfikator flagi (np. "mobile") |
| `display_name` | str | Nazwa do wyświetlenia |
| `description` | str\|None | Opis działania |
| `is_active` | bool | |
| `created_at` | datetime UTC | |

**Relacje:** `scenario_flags` → `ScenarioFlag` (1:N, cascade delete)

---

## ScenarioFlag (`app/models/flag_definition.py`)

Powiązanie scenariusza z flagą — określa wartość flagi dla konkretnego scenariusza.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `scenario_id` | FK → Scenario (cascade) | |
| `flag_id` | FK → FlagDefinition (cascade) | |
| `is_enabled` | bool (default: True) | Wartość flagi dla tego scenariusza |

---

## BasketSnapshot (`app/models/basket_snapshot.py`)

Snapshot stanu koszyka w danym etapie.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `run_id` | FK → ScenarioRun | |
| `stage` | str | Etap: home/listing/cart0/cart1/cart4 |
| `product_price` | Numeric(10,2)\|None | |
| `delivery_price` | Numeric(10,2)\|None | |
| `total_price` | Numeric(10,2)\|None | |
| `raw_data` | JSON | Pełny snapshot (screenshoty, dane) |
| `captured_at` | datetime UTC | |

---

## ApiError (`app/models/api_error.py`)

Błąd HTTP zarejestrowany podczas wykonywania scenariusza.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `run_id` | FK → ScenarioRun | |
| `endpoint` | str | URL żądania |
| `method` | str | GET/POST/PUT/DELETE |
| `status_code` | int | Kod HTTP (>400) |
| `response_body` | str\|None | Treść odpowiedzi (obcięta do 250 znaków) |
| `captured_at` | datetime UTC | |

---

## ApiErrorExclusion (`app/models/api_error_exclusion.py`)

Wzorzec wykluczenia znanych/oczekiwanych błędów API.

| Pole | Typ | Opis |
|---|---|---|
| `id` | PK int | |
| `endpoint_pattern` | str | Fragment URL do wykluczenia |
| `status_code` | int\|None | Opcjonalny kod HTTP |
| `response_body_pattern` | str\|None | Fragment treści odpowiedzi |
| `note` | str | Uzasadnienie wykluczenia |
| `created_at` | datetime UTC | |

---

## WAL mode (`database.py`)

SQLite WAL (Write-Ahead Logging) włączony przez event listener przy każdym połączeniu:

```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, ...):
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
```

**Efekt:** Umożliwia równoległe odczyty i zapisy podczas wykonywania wielu scenariuszy jednocześnie. Eliminuje błąd "database is locked".

Dla MySQL: WAL nie jest wymagany — `connect_args` jest pusty.

---

## Jak dodać nową tabelę

1. `app/models/new_table.py` — klasa dziedzicząca `Base`
2. Import w `app/models/__init__.py`
3. `alembic revision --autogenerate -m "add new_table"`
4. `alembic upgrade head`

Szczegóły: [HOW_TO_EXTEND.md](HOW_TO_EXTEND.md).
