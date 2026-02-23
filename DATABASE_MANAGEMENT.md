# Database Management — Zarządzanie bazą danych

## Szybki Start

### Windows (dwuklik)
- **`reset.bat`** — Pełny reset bazy (usuwa wszystko, tworzy od nowa)
- **`clean.bat`** — Usuwa tylko runy (zachowuje konfigurację)
- **`test.bat`** — Uruchom suite #1 na RC
- **`panel.bat`** — Uruchom panel webowy

### Terminal
```bash
# Pełny reset
python reset_database.py

# Tylko runy
python clean_runs.py

# Test
python main.py --suite 1 --environment 1

# Panel
python run_panel.py
```

---

## `reset_database.py` — Pełny Reset

**Co robi:**
1. Usuwa `shop_monitor.db` (+ WAL files)
2. Uruchamia `alembic upgrade head` (tworzy strukturę)
3. Uruchamia `seed.py` (environments, suites, scenarios)
4. Uruchamia `seed_alert_types.py` (typy alertów)

**Opcje:**
```bash
# Interaktywne (pyta o potwierdzenie)
python reset_database.py

# Bez pytania
python reset_database.py --force

# Bez seeda (tylko struktura)
python reset_database.py --keep-seed
```

**Kiedy używać:**
- Po zmianach w modelach (nowe kolumny, tabele)
- Gdy migracja się wywala
- Gdy chcesz czyste środowisko
- Po refactorze alertów (nowa struktura)

---

## `clean_runs.py` — Czyszczenie Runów

**Co robi:**
1. Usuwa wszystkie runy: `suite_runs`, `scenario_runs`
2. Usuwa dane testów: `alerts`, `alert_groups`, `basket_snapshots`, `api_errors`
3. Usuwa logi z `logs/`

**Zachowuje:**
- Konfigurację: `suites`, `scenarios`, `environments`
- Powiązania: `suite_scenarios`, `suite_environments`
- Alerty: `alert_configs`, `alert_types`

**Opcje:**
```bash
# Interaktywne
python clean_runs.py

# Bez pytania
python clean_runs.py --force

# Zachowaj logi
python clean_runs.py --keep-logs
```

**Kiedy używać:**
- Przed nowym cyklem testów
- Gdy baza jest pełna starych runów
- Chcesz zacząć od czystej karty ale zachować konfigurację

---

## Workflow: Refactor Alertów

### Opcja 1: Pełny Reset (zalecane)
```bash
# Windows
reset.bat

# Linux/Mac
python reset_database.py --force
```

**Zalety:**
- Czysta baza z nową strukturą
- Nie trzeba martwić się migracją
- Szybkie (10 sekund)

**Wady:**
- Tracisz dane testowe (ale nie konfigurację!)

---

### Opcja 2: Migracja (jeśli masz ważne dane)

```bash
# 1. Backup
copy shop_monitor.db shop_monitor_backup.db

# 2. Wygeneruj migrację
alembic revision --autogenerate -m "alerts refactor"

# 3. RĘCZNIE EDYTUJ plik migracji (patrz MIGRATION_ALERTS_REFACTOR.md)

# 4. Zastosuj
alembic upgrade head

# 5. Jeśli coś pójdzie nie tak
copy shop_monitor_backup.db shop_monitor.db
```

**Zalety:**
- Zachowujesz historyczne dane

**Wady:**
- Trzeba ręcznie edytować migrację
- Może się wywrócić (SQLite + foreign keys)

---

## Codzienne Użycie

### Przed testami
```bash
python clean_runs.py --force   # wyczyść stare runy
python main.py --suite 1 --environment 1
```

### Po zmianach w kodzie
```bash
python reset_database.py --force  # pełny reset
```

### Uruchomienie suite
```bash
# Cała suite
python main.py --suite 1 --environment 1

# Pojedynczy scenariusz
python main.py --scenario 5 --environment 1

# Headless (bez okna przeglądarki)
python main.py --suite 1 --environment 1 --headless
```

---

## Troubleshooting

### Problem: Foreign key constraint
```bash
# SQLite czasem ma problemy z foreign keys podczas migracji
# Rozwiązanie: pełny reset
python reset_database.py --force
```

### Problem: Migracja się wywala
```bash
# Rollback
alembic downgrade -1

# Lub pełny reset
python reset_database.py --force
```

### Problem: Baza jest locked
```bash
# Zamknij wszystkie połączenia (panel, Python REPL)
# Potem:
python reset_database.py --force
```

### Problem: Makefile nie działa na Windows
```bash
# Użyj .bat zamiast make:
reset.bat      # zamiast: make reset
clean.bat      # zamiast: make clean
```

---

## Best Practices

### Rozwój
- **Przed każdym testem:** `clean_runs.py`
- **Po zmianach w modelach:** `reset_database.py`
- **Codziennie rano:** `clean_runs.py` (czysty start)

### Produkcja
- **NIE używaj** `reset_database.py` (tracisz dane!)
- Używaj migracji: `alembic upgrade head`
- Backup przed każdą migracją

### Testy
```bash
# Cykl testowy
python reset_database.py --force    # 1. Czysta baza
python main.py --suite 1 --env 1    # 2. Uruchom testy
python run_panel.py                 # 3. Zobacz wyniki
python clean_runs.py --force        # 4. Wyczyść przed następnym cyklem
```

---

## Pliki w `.gitignore`

Upewnij się że masz:
```gitignore
*.db
*.db-shm
*.db-wal
logs/
```

Baza danych NIE powinna być w repo!

---

## Szybkie Komendy (Cheat Sheet)

```bash
# RESET (wszystko od nowa)
python reset_database.py --force

# CLEAN (tylko runy)
python clean_runs.py --force

# TEST (uruchom suite)
python main.py --suite 1 --environment 1

# PANEL (webowy UI)
python run_panel.py

# SEED (tylko dane startowe, bez reset)
python seed.py
python seed_alert_types.py
```
