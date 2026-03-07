# System alertów

Plik opisuje działanie `AlertEngine`, wymóg `AlertConfig`, typy alertów oraz maszynę stanów `AlertGroup`.

---

## AlertEngine (`core/alert_engine.py`)

Zbiera i filtruje alerty podczas wykonywania scenariusza. **Jedyne miejsce** gdzie alert trafia do bazy.

```python
class AlertEngine:
    def __init__(self, run_id, scenario_id, environment_id, db): ...
    def add_alert(self, rule: str, description: str | None = None): ...
    def counted_alerts(self) -> int: ...
    def save_all(self): ...
```

### `add_alert(rule, description=None)`

Kroki filtrowania:

```
1. Zapytanie: AlertConfig WHERE business_rule = rule
2. Brak konfiguracji?     → LOG debug, return (cichy ignore)
3. is_active = False?     → LOG debug, return (cichy ignore)
4. is_disabled_now()?     → LOG debug, return (harmonogram)
5. Utwórz Alert (nie zapisuj jeszcze)
6. Dołącz do self.alerts
7. LOG info
```

**KRYTYCZNA ZASADA:** Każdy `business_rule` musi mieć odpowiedni `AlertConfig` w DB. Bez niego alert jest **cicho ignorowany** — nie pojawi się nigdzie w UI.

Uwaga: `AlertEngine.add_alert()` przyjmuje 2 argumenty (`rule`, `description`), ale `ScenarioExecutor._register_alerts()` wywołuje `add_alert(business_rule, description, alert_type)`. `alert_type` jest pobierany z `AlertConfig` — parametr z `AlertResult` jest ignorowany przez obecną implementację AlertEngine.

### `counted_alerts() → int`

Liczba alertów które przeszły filtrowanie. Używana przez `ScenarioExecutor` do decyzji `SUCCESS`/`FAILED`.

### `save_all()`

`db.add_all(self.alerts)` + `db.flush()` — zapisuje wszystkie zebrane alerty jednym wywołaniem.

---

## Wymóg AlertConfig

Bez `AlertConfig` w DB żaden alert nie dotrze do UI. To celowy mechanizm gatekeepingu:

- Pozwala wdrożyć nową regułę do kodu bez natychmiastowego efektu w produkcji
- Pozwala wyłączyć hałaśliwe alerty bez zmiany kodu
- Pozwala skonfigurować okna wyłączeń (harmonogram)

**Jak dodać nowy alert:** patrz [HOW_TO_EXTEND.md](HOW_TO_EXTEND.md).

---

## AlertType (`app/models/alert_type.py`)

Seeded przez `seed_alert_types.py`. Zmiany przez panel `/alert-configs`.

| Slug | Kolor | Znaczenie |
|---|---|---|
| `bug` | czerwony | Błąd produkcyjny wymagający szybkiej reakcji |
| `to_verify` | żółty | Do weryfikacji — może być fałszywy alarm |
| `to_improve` | pomarańczowy | Do poprawy, ale nie krytyczny |
| `disabled` | szary | Alert wyłączony / nieistotny |

---

## AlertConfig (`app/models/alert_config.py`)

Konfiguracja dla jednego `business_rule`. UNIQUE constraint na `business_rule`.

| Pole | Typ | Opis |
|---|---|---|
| `business_rule` | str (unique) | Identyfikator reguły (np. `CART1_DELIVERY_UNAVAILABLE`) |
| `name` | str | Tytuł alertu wyświetlany w UI |
| `alert_type_id` | FK → AlertType | Typ alertu (kolor, znaczenie) |
| `is_active` | bool | False = wszystkie alerty tej reguły ignorowane |
| `disabled_from_date` | date\|None | Harmonogram wyłączenia — data od |
| `disabled_to_date` | date\|None | Harmonogram wyłączenia — data do |
| `disabled_from_time` | time\|None | Harmonogram wyłączenia — czas od |
| `disabled_to_time` | time\|None | Harmonogram wyłączenia — czas do |

### `is_disabled_now()` → bool

Sprawdza czy obecny czas UTC mieści się w oknie wyłączenia. Używane przez `AlertEngine.add_alert()`.

---

## AlertGroup — maszyna stanów

`AlertGroup` to deduplikator alertów na poziomie suite. Jeden `AlertGroup` odpowiada jednemu unikalnemu problemowi (business_rule + scenariusze) w danym środowisku.

### Stany (statusy)

```
          ┌────────────────────────────────────────┐
          │                                        │
    OPEN ──► IN_PROGRESS ──► AWAITING_FIX          │  (ponowne wystąpienie)
          │              └──► AWAITING_TEST_UPDATE  │ ──────────────────────► OPEN
          │                                        │
          └──────────── CLOSED ◄───────────────────┘
                    (NAB / CANT_REPRODUCE → OPEN przy powrocie)
                    (DUPLICATE → cichy repeat gdy parent w AWAITING_*)
```

| Status | Opis |
|---|---|
| `OPEN` | Nowo wykryty problem |
| `IN_PROGRESS` | Ktoś przypisany, weryfikuje |
| `AWAITING_FIX` | Zgłoszono do deweloperów, czekamy na deploy |
| `AWAITING_TEST_UPDATE` | Scenariusz do aktualizacji |
| `CLOSED` | Rozwiązany / zamknięty |

### Typy rozwiązań (`resolution_type`)

| Wartość | Status po zamknięciu | Opis |
|---|---|---|
| `bug` | AWAITING_FIX | Prawdziwy błąd, zgłoszony do dewelopera |
| `needs_dev` | AWAITING_FIX | Wymaga zmiany kodu |
| `config` | AWAITING_FIX | Błąd konfiguracji |
| `script_fix` | AWAITING_TEST_UPDATE | Skrypt testowy do naprawy |
| `scenario_fix` | AWAITING_TEST_UPDATE | Scenariusz do aktualizacji |
| `nab` | CLOSED | Not a bug — celowe zachowanie |
| `duplicate` | CLOSED | Duplikat innego alertu |
| `cant_reproduce` | CLOSED | Nie można odtworzyć |

---

## Pola AlertGroup

| Pole | Typ | Opis |
|---|---|---|
| `business_rule` | str | Identyfikator reguły |
| `alert_type` | str | Slug AlertType (snapshot z chwili powstania) |
| `title` | str | Tytuł (snapshot z AlertConfig.name) |
| `occurrence_count` | int | Liczba wystąpień w ostatnim suite_run |
| `scenario_ids` | JSON str | Posortowane ID scenariuszy w których wystąpił |
| `repeat_count` | int | Łączna liczba suite_runów z tym alertem |
| `clean_runs_count` | int | Liczba suite_runów BEZ tego alertu od ostatniego wystąpienia |
| `status` | Enum | Aktualny stan (OPEN, IN_PROGRESS, ...) |
| `first_seen_at` | datetime | Kiedy alert pojawił się po raz pierwszy |
| `last_seen_at` | datetime | Kiedy alert pojawił się ostatnio |
| `suite_run_history` | JSON list | Lista ID suite_runów w których wystąpił |
| `last_suite_run_id` | FK | Ostatni suite_run z tym alertem |
| `duplicate_of_id` | FK (self) | Jeśli DUPLICATE — ID nadrzędnego AlertGroup |

---

## Algorytm deduplikacji (`SuiteExecutor._finalize_suite_run`)

Po zakończeniu suite, dla każdego unikalnego `business_rule` zebranego w tym runie:

### Krok 1: Alert wystąpił

```python
_handle_alert_occurred(suite_run, group_data)
```

1. Szukaj kandydatów: `AlertGroup` dla tego `business_rule` + nie-CLOSED + to samo `environment_id`
2. Dopasowanie: `_find_matching_candidate()` — `scenario_ids` to subset/superset nowych
3. **Jeśli znaleziono kandydata** → `_update_existing_alert()`:
   - Scala `scenario_ids` (union)
   - `repeat_count += 1`
   - `clean_runs_count = 0`
   - Dołącza `suite_run.id` do `suite_run_history`
4. **Jeśli nie znaleziono** → szukaj CLOSED DUPLICATE z aktywnym parentem → `_update_duplicate_alert()` (cichy repeat)
5. **Jeśli nie ma CLOSED DUPLICATE** → szukaj CLOSED (NAB/CANT_REPRODUCE) → `_reopen_alert()`:
   - `status = OPEN`
   - `repeat_count += 1`
   - `clean_runs_count = 0`
   - **Nie czyści `resolution_type`** — zachowany jako kontekst ("poprzednio: NAB")
6. **Brak czegokolwiek** → `_create_new_alert()` → nowy `AlertGroup`

### Krok 2: Alert NIE wystąpił

```python
_handle_alerts_not_occurred(suite_run, active_rules)
```

Dla wszystkich aktywnych `AlertGroup` (nie-CLOSED) dla tego environment:
- Jeśli `business_rule` nie ma w `active_rules` → `clean_runs_count += 1`

System automatycznie nie zamyka alertów — decyzja po stronie użytkownika w panelu.

---

## Matching `scenario_ids`

Dopasowanie przez subset/superset — elastyczne dla sytuacji gdy zestaw scenariuszy zmienia się:

```python
new_ids = {1, 2, 3}
existing_ids = {1, 2}    # subset → MATCH (nowe scenariusze zostały dodane)

new_ids = {1}
existing_ids = {1, 2, 3} # superset → MATCH (część scenariuszy zniknęła)
```

Po dopasowaniu `scenario_ids` jest scalane (union), więc `AlertGroup` akumuluje wszystkie scenariusze gdzie kiedykolwiek wystąpił problem.

---

## `clean_runs_count`

Licznik suite_runów bez danego alertu od ostatniego wystąpienia. Nie służy do automatycznego zamykania — to informacja dla użytkownika:

> "Alert nie pojawia się od 5 runów — być może fix został wdrożony"

Po wystąpieniu alertu zawsze resetowany do 0.
