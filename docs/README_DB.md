# Baza Danych — Instrukcja

## Instalacja

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Pierwsze uruchomienie — tworzenie bazy

```bash
# 1. Wygeneruj pierwsza migracje na podstawie modeli
alembic revision --autogenerate -m "inicjalna struktura bazy"

# 2. Zastosuj migracje — tworzy plik shop_monitor.db
alembic upgrade head
```

Po tych dwoch komendach masz gotowa baze SQLite z wszystkimi tabelami.

## Gdy dodasz nowe pole do modelu

Przyklad: dodajesz pole "user_agent" do tabeli scenarios.

```bash
# 1. Edytujesz scenario.py — dodajesz pole
# 2. Generujesz migracje
alembic revision --autogenerate -m "dodaj user_agent do scenarios"

# 3. Aplikujesz zmiane
alembic upgrade head
```

Dane w bazie zostaja — tylko nowa kolumna zostaje dodana.

## Migracja SQLite → MySQL

Zmien jedna linie w alembic.ini:
  sqlalchemy.url = mysql+pymysql://user:password@localhost/shop_monitor

Lub ustaw zmienna srodowiskowa:
  set DATABASE_URL=mysql+pymysql://user:password@localhost/shop_monitor

Potem uruchom:
  alembic upgrade head

## Struktura tabel

environments       — srodowiska PRE/RC/PROD
suites             — grupy scenariuszy
suite_environments — relacja suite <-> environment (z kronem i workers)
suite_scenarios    — relacja suite <-> scenario (scenariusz w wielu suite)
scenarios          — pojedyncze scenariusze
scenario_runs      — historia uruchomien
basket_snapshots   — stany koszyka per etap
api_errors         — bledy HTTP 4xx/5xx
alerts             — alerty biznesowe
alert_configs      — konfiguracja typow alertow
