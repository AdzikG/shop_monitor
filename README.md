# Shop Monitor

Narzędzie do monitorowania procesów koszykowych e-commerce z panelem webowym (FastAPI + Playwright + SQLite/MySQL).

## Wymagania

- Python 3.11+
- Git

## Instalacja

```bash
# 1. Utwórz i aktywuj wirtualne środowisko (Windows)
python -m venv venv
venv\Scripts\activate

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Zainstaluj przeglądarkę Chromium
playwright install chromium

# 4. Utwórz bazę danych i załaduj dane startowe
alembic upgrade head
python seed.py
python seed_alert_types.py
```

## Uruchomienie panelu webowego

```bash
python run_panel.py
```

Panel dostępny pod adresem: http://127.0.0.1:8000

## Uruchomienie scenariuszy

```bash
# Pierwszy aktywny suite (domyślnie)
python main.py

# Wybrany suite na wybranym środowisku, 2 równoległe scenariusze
python main.py --suite 1 --environment 1 --workers 2

# Pojedynczy scenariusz
python main.py --scenario 5 --environment 1

# Tryb headless (bez okna przeglądarki)
python main.py --suite 1 --environment 1 --headless
```

## Konfiguracja MySQL (opcjonalnie)

Domyślnie aplikacja używa SQLite. Aby przełączyć na MySQL:

**1. Utwórz bazę danych w MySQL:**

```sql
CREATE DATABASE shop_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**2. Dodaj `DATABASE_URL` do pliku `.env`:**

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/shop_monitor
```

**3. Zaktualizuj `alembic.ini` (linia `sqlalchemy.url`):**

```ini
sqlalchemy.url = mysql+pymysql://user:password@localhost:3306/shop_monitor
```

**4. Zastosuj migracje i załaduj dane:**

```bash
alembic upgrade head
python seed.py
python seed_alert_types.py
```

## Struktura katalogów

```
shop_monitor/
├── app/                  # panel webowy (FastAPI + Jinja2 + HTMX)
│   ├── models/           # modele SQLAlchemy
│   ├── routers/          # endpointy API
│   └── templates/        # szablony HTML
├── core/                 # silnik alertów, rejestr uruchomień
├── scenarios/            # logika scenariuszy
│   ├── pages/            # Page Object Model (Playwright)
│   └── rules/            # reguły biznesowe
├── alembic/              # migracje bazy danych
├── main.py               # punkt startowy CLI
├── run_panel.py          # punkt startowy panelu
├── seed.py               # dane startowe (środowiska, suite, scenariusze)
└── seed_alert_types.py   # typy alertów
```
