# Shop Monitor POC

Proof of Concept — monitoring procesów koszykowych z Playwright async + POM + Alert Engine.

## Struktura

```
shop_monitor_poc/
├── pages/
│   ├── base_page.py              # klasa bazowa POM
│   └── cart/
│       └── cart_0_list.py        # listing + dodanie do koszyka
├── core/
│   └── alert_engine.py           # silnik alertów → JSON
├── scenarios/
│   ├── scenario_executor.py      # orchestrator scenariusza
│   └── scenarios.json            # konfiguracja scenariuszy
├── main.py                       # punkt startowy
├── requirements.txt
└── results/                      # tutaj trafiają wyniki (tworzony automatycznie)
```

## Instalacja

```bash
# 1. Utwórz wirtualne środowisko
python -m venv venv

# 2. Aktywuj (Windows)
venv\Scripts\activate

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Zainstaluj przeglądarkę Chromium
playwright install chromium
```

## Uruchomienie

```bash
# Domyślnie — 2 scenariusze równolegle, widać okno przeglądarki
python main.py

# Bez okna przeglądarki (jak na serwerze Linux)
python main.py --headless

# Zmień liczbę równoległych scenariuszy
python main.py --workers 3
```

## Wyniki

Po uruchomieniu w folderze `results/` znajdziesz:
- `*.log` — pełny log uruchomienia
- `YYYY-MM-DD_HH-MM-SS/` — folder z wynikami
  - `{run_id}.json` — alerty i wyniki scenariusza
  - `{run_id}/` — screenshoty z każdego etapu

## Dodawanie scenariuszy

Edytuj plik `scenarios/scenarios.json`:

```json
[
  {
    "name": "Nazwa scenariusza",
    "listing_url": "https://www.amazon.pl/s?k=szukana+fraza",
    "should_order": false,
    "extra_params": {}
  }
]
```

## Przykładowy wynik JSON

```json
{
  "run_id": "Elektronika_laptop_a1b2c3d4",
  "scenario_name": "Elektronika - laptop",
  "status": "success",
  "total_alerts": 0,
  "counted_alerts": 0,
  "alerts": []
}
```
