# Shop Monitor — CLI Commands Reference

## Instalacja i Setup

### Pierwsze uruchomienie projektu

```bash
# 1. Utwórz i aktywuj środowisko wirtualne
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Zainstaluj przeglądarki Playwright
playwright install chromium

# Linux - dodatkowe zależności systemowe
playwright install-deps

# 4. Inicjalizuj bazę danych
alembic revision --autogenerate -m "inicjalna struktura"
alembic upgrade head

# 5. Wypełnij bazę przykładowymi danymi
python seed.py
```

---

## Baza Danych (Alembic)

### Tworzenie i aplikowanie migracji

```bash
# Wygeneruj migrację po zmianie modeli
alembic revision --autogenerate -m "opis zmiany"

# Zastosuj wszystkie migracje
alembic upgrade head

# Cofnij jedną migrację
alembic downgrade -1

# Zobacz historię migracji
alembic history

# Zobacz aktualną wersję bazy
alembic current

# Cofnij do konkretnej wersji
alembic downgrade <revision_id>
```

### Resetowanie bazy

```bash
# Usuń bazę i zbuduj od nowa
rm shop_monitor.db
rm alembic/versions/*.py
alembic revision --autogenerate -m "inicjalna struktura"
alembic upgrade head
python seed.py
```

---

## Uruchamianie Scenariuszy (CLI)

### Podstawowe użycie

```bash
# Uruchom domyślną suite na domyślnym środowisku
python main.py

# Konkretna suite i środowisko
python main.py --suite 1 --environment 1

# Z określoną liczbą workers
python main.py --suite 1 --environment 1 --workers 4

# W trybie headless (bez okna przeglądarki)
python main.py --suite 1 --environment 1 --headless

# Wszystkie opcje razem
python main.py --suite 1 --environment 1 --workers 2 --headless
```

### Parametry

| Parametr | Opis | Domyślnie |
|----------|------|-----------|
| `--suite <id>` | ID suite do uruchomienia | Pierwsza aktywna suite |
| `--environment <id>` | ID środowiska (PRE/RC/PROD) | Pierwsze aktywne środowisko |
| `--workers <n>` | Liczba równoległych scenariuszy | Z konfiguracji suite |
| `--headless` | Uruchom bez okna przeglądarki | False (z oknem) |

### Przykłady

```bash
# Suite "Bez zamówień" na PRE z 2 workers
python main.py --suite 1 --environment 1 --workers 2

# Suite "Top 1000" na PROD w tle (headless)
python main.py --suite 2 --environment 2 --headless

# Debugowanie - jeden worker, z oknem
python main.py --suite 1 --environment 1 --workers 1
```

---

## Panel Webowy

### Uruchamianie panelu

```bash
# Domyślnie - localhost:8000
python run_panel.py

# Inny port
python run_panel.py --port 8080

# Dostęp z sieci (np. dla teamu)
python run_panel.py --host 0.0.0.0

# Kombinacja
python run_panel.py --host 0.0.0.0 --port 8080
```

### Parametry

| Parametr | Opis | Domyślnie |
|----------|------|-----------|
| `--port <n>` | Port HTTP | 8000 |
| `--host <ip>` | Adres IP | 127.0.0.1 (tylko localhost) |

### Dostęp do panelu

```bash
# Lokalnie
http://127.0.0.1:8000

# Z sieci (gdy --host 0.0.0.0)
http://<IP_SERWERA>:8000
```

**Panel oferuje:**
- Dashboard z auto-refreshem
- Lista suite runs
- Zakładka Alerts z filtrowaniem
- Formularz uruchamiania suite

---

## Zarządzanie Danymi

### Seed - wypełnienie bazy przykładowymi danymi

```bash
python seed.py
```

**Tworzy:**
- 2 środowiska: PRE, PROD
- 1 suite: "Bez zamówień"
- 2 scenariusze: "Elektronika - laptop", "Książki - Python"
- Powiązania suite ↔ environment ↔ scenario

### Clean - czyszczenie runów

```bash
python clean_runs.py
```

**Usuwa:**
- suite_runs
- scenario_runs
- alerts
- alert_groups
- basket_snapshots
- api_errors

**Zachowuje:**
- environments
- suites
- scenarios
- suite_scenarios
- alert_configs

Prosi o potwierdzenie przed usunięciem.

---

## Logi

### Gdzie są logi?

```bash
# Logi CLI (main.py)
logs/run_YYYYMMDD_HHMMSS.log

# Logi panelu webowego
# Drukowane w konsoli gdzie uruchomiono run_panel.py
```

### Przeglądanie logów

```bash
# Ostatni log
ls -lt logs/ | head -n 2

# Windows
dir logs /o-d

# Otwórz w edytorze
code logs/run_20260215_210930.log

# Tail (Linux/Mac)
tail -f logs/run_20260215_210930.log
```

---

## Python REPL - Interaktywne Zarządzanie

### Uruchomienie REPL z dostępem do bazy

```bash
python
```

```python
from database import SessionLocal
from app.models import *

db = SessionLocal()

# Lista wszystkich suite
suites = db.query(Suite).all()
for s in suites:
    print(f"{s.id}: {s.name}")

# Lista scenariuszy w suite
suite = db.query(Suite).first()
for ss in suite.suite_scenarios:
    print(f"  {ss.scenario.name}")

# Ostatnie suite run
latest = db.query(SuiteRun).order_by(SuiteRun.started_at.desc()).first()
print(f"Suite Run #{latest.id}: {latest.status}")
print(f"Success: {latest.success_scenarios}, Failed: {latest.failed_scenarios}")

# Alerty z ostatniego runu
for ag in latest.alert_groups:
    print(f"{ag.business_rule}: {ag.occurrence_count}x")

# Zamknij sesję
db.close()
```

### Tworzenie scenariusza ręcznie

```python
from database import SessionLocal
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario

db = SessionLocal()

# Nowy scenariusz
scenario = Scenario(
    name="AGD - pralka",
    listing_urls=["https://www.amazon.pl/s?k=pralka"],
    delivery_name="Kurier",
    payment_name="Karta",
    postal_code="00-001",
    should_order=False
)
db.add(scenario)
db.commit()
db.refresh(scenario)

# Dodaj do suite
suite_id = 1  # ID suite "Bez zamówień"
link = SuiteScenario(
    suite_id=suite_id,
    scenario_id=scenario.id,
    order=3  # kolejność w suite
)
db.add(link)
db.commit()

print(f"Utworzono scenariusz #{scenario.id}: {scenario.name}")
db.close()
```

---

## Testowanie i Debugowanie

### Uruchom jeden scenariusz lokalnie (debug)

```bash
# Jeden worker, z oknem przeglądarki, szczegółowe logi
python main.py --suite 1 --environment 1 --workers 1
```

### Sprawdź status bazy

```bash
# Uruchom DB Browser for SQLite
# Otwórz shop_monitor.db
# Sprawdź zawartość tabel
```

### Weryfikacja środowiska

```bash
# Sprawdź wersję Pythona (wymaga 3.10+)
python --version

# Sprawdź czy Playwright zainstalowany
playwright --version

# Lista zainstalowanych pakietów
pip list

# Sprawdź czy przeglądarka dostępna
playwright show-trace
```

---

## Zmienne Środowiskowe

### Konfiguracja przez .env

Utwórz plik `.env` w głównym katalogu:

```bash
# .env
DATABASE_URL=sqlite:///./shop_monitor.db

# Dla MySQL
# DATABASE_URL=mysql+pymysql://user:password@localhost/shop_monitor
```

### Użycie

```bash
# Python automatycznie wczyta z .env jeśli używasz python-dotenv
python main.py
python run_panel.py
```

---

## Workflow - Typowe Scenariusze

### 1. Świeży start projektu

```bash
# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Baza
alembic revision --autogenerate -m "init"
alembic upgrade head
python seed.py

# Uruchom panel
python run_panel.py
```

Otwórz `http://127.0.0.1:8000` i kliknij Run.

### 2. Dodanie nowego scenariusza

```bash
# Opcja A: Python REPL (jak wyżej)
python
>>> from database import SessionLocal
>>> # ... kod tworzenia scenariusza

# Opcja B: Edycja seed.py i ponowne uruchomienie
python clean_runs.py  # wyczyść stare runy
python seed.py        # dodaj nowe scenariusze
```

### 3. Zmiana modelu bazy danych

```bash
# 1. Edytuj model w app/models/
code app/models/scenario.py

# 2. Wygeneruj migrację
alembic revision --autogenerate -m "dodaj pole user_agent"

# 3. Zastosuj
alembic upgrade head

# 4. Sprawdź w DB Browser
```

### 4. Debugging nie działającego scenariusza

```bash
# 1. Uruchom z oknem i jednym workerem
python main.py --suite 1 --environment 1 --workers 1

# 2. Obserwuj przeglądarkę
# 3. Sprawdź logi
tail -f logs/run_*.log

# 4. Sprawdź alerty w bazie
python
>>> from database import SessionLocal
>>> db = SessionLocal()
>>> alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(5).all()
>>> for a in alerts:
...     print(f"{a.business_rule}: {a.title}")
```

### 5. Porównanie wyników RC vs PROD

```bash
# 1. Uruchom suite na RC
python main.py --suite 1 --environment 1

# 2. Uruchom suite na PROD
python main.py --suite 1 --environment 2

# 3. Sprawdź w panelu
# Dashboard → kliknij suite run → porównaj alerty
```

---

## Skróty i Aliasy (opcjonalnie)

### Windows (PowerShell profile)

Dodaj do `$PROFILE`:

```powershell
# C:\Users\<user>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1

function Start-ShopMonitor {
    param([int]$suite = 1, [int]$env = 1, [int]$workers = 2)
    python main.py --suite $suite --environment $env --workers $workers
}

function Start-Panel {
    python run_panel.py
}

# Użycie
# Start-ShopMonitor -suite 1 -env 1 -workers 4
# Start-Panel
```

### Linux/Mac (bash/zsh)

Dodaj do `~/.bashrc` lub `~/.zshrc`:

```bash
# Aliasy Shop Monitor
alias sm-run='python main.py'
alias sm-panel='python run_panel.py'
alias sm-clean='python clean_runs.py'
alias sm-seed='python seed.py'
alias sm-logs='ls -lt logs/ | head -n 5'

# Użycie
# sm-run --suite 1 --environment 1 --workers 2
# sm-panel
```

---

## Rozwiązywanie Problemów

### "alembic: command not found"

```bash
# Środowisko nie aktywowane
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### "database is locked"

```bash
# Sprawdź czy database.py ma WAL mode
grep "PRAGMA journal_mode=WAL" database.py

# Jeśli nie ma - dodaj event listener (patrz ARCHITECTURE.md)
```

### "playwright: executable doesn't exist"

```bash
# Przeglądarka nie zainstalowana
playwright install chromium

# Linux - brakujące zależności
playwright install-deps
```

### "ModuleNotFoundError: No module named 'app'"

```bash
# Uruchamiasz z niewłaściwego katalogu
cd shop_monitor  # przejdź do głównego katalogu projektu
python main.py
```

### Panel nie odświeża się automatycznie

```bash
# Sprawdź w devtools przeglądarki czy HTMX działa
# Ctrl+Shift+I → Network → filtruj "runs-table"
# Powinny być requesty co 15s

# Jeśli nie ma - sprawdź dashboard.html czy ma:
# hx-trigger="load, every 15s"
```

---

## Podsumowanie Najczęstszych Komend

```bash
# ═══════════════════════════════════════
# CODZIENNE UŻYCIE
# ═══════════════════════════════════════

# Aktywuj środowisko
venv\Scripts\activate

# Uruchom panel
python run_panel.py

# Uruchom scenariusze z CLI
python main.py --suite 1 --environment 1

# Wyczyść stare runy
python clean_runs.py

# ═══════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════

# Zmiana modeli → migracja
alembic revision --autogenerate -m "opis"
alembic upgrade head

# Reset bazy
rm shop_monitor.db alembic/versions/*.py
alembic revision --autogenerate -m "init"
alembic upgrade head
python seed.py

# Debugowanie
python main.py --suite 1 --environment 1 --workers 1

# ═══════════════════════════════════════
# PRZYDATNE
# ═══════════════════════════════════════

# Zobacz logi
dir logs /o-d  # Windows
ls -lt logs/   # Linux/Mac

# Python REPL z bazą
python
>>> from database import SessionLocal
>>> db = SessionLocal()
>>> # query bazy...
```
