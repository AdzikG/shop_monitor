# Migracja Alert Configs — Instrukcja

## Zmiany w Systemie Alertów

### Co się zmienia?

**Przed:**
- Alerty były twardym kodem w AlertEngine
- Typy alertów (bug/verify/disabled) były ENUM w kodzie
- Nie było kontroli nad tym które alerty są wyświetlane

**Po:**
- Alerty konfigurowane przez panel webowy
- Typy alertów w osobnej tabeli (można dodawać nowe)
- **TYLKO alerty z konfiguracją są wyświetlane**
- Harmonogram wyłączeń (data + godzina)
- On/Off switch per alert

### Nowe Tabele

**alert_types**
- id, name, slug, color, description, is_active
- Przykłady: "Błąd" (bug), "Do weryfikacji" (to_verify), "Do poprawy" (to_improve)

**alert_configs** (rozszerzona)
- Podstawowe: name, business_rule, alert_type_id, description
- Harmonogram: disabled_from_date, disabled_to_date, disabled_from_time, disabled_to_time
- Kontrola: is_active, updated_by

## Kroki Migracji

### 1. Backup Bazy

```bash
copy shop_monitor.db shop_monitor_backup_$(date +%Y%m%d).db
```

### 2. Nadpisz Pliki

Rozpakuj paczkę i podmień:
- `app/models/alert_type.py` (NOWY)
- `app/models/alert_config.py` (ZAKTUALIZOWANY)
- `app/models/__init__.py`
- `core/alert_engine.py` (PRZEPISANY)
- `app/routers/alert_configs.py` (NOWY)
- `app/main.py`
- `app/templates/base.html`
- `app/templates/alert_configs_list.html` (NOWY)
- `app/templates/alert_config_detail.html` (NOWY)
- `app/templates/alert_config_form.html` (NOWY)
- `seed_alert_types.py` (NOWY)

### 3. Wygeneruj Migrację

```bash
alembic revision --autogenerate -m "add alert_types and update alert_configs"
```

### 4. Zastosuj Migrację

```bash
alembic upgrade head
```

### 5. Wypełnij Domyślne Typy Alertów

```bash
python seed_alert_types.py
```

Utworzy 4 typy:
- Błąd (bug) — czerwony
- Do weryfikacji (to_verify) — żółty
- Do poprawy (to_improve) — pomarańczowy
- Wyłączony (disabled) — szary

### 6. Skonfiguruj Alerty

**WAŻNE:** Po migracji żadne alerty nie będą się wyświetlać dopóki nie dodasz ich w panelu.

Przejdź do **Alert Configs** w nawigacji i dodaj konfiguracje dla alertów które chcesz widzieć.

Przykład:
```
Name: Brak produktów na listingu
Business Rule: listing.no_products
Type: Błąd
Description: Listing nie zwraca żadnych produktów
Active: ✓
```

## Przykłady Użycia

### Harmonogram Wyłączeń

**Scenariusz:** Alert "kalendarz niedostępny" ma być wyłączony w weekendy.

```
Name: Kalendarz niedostępny w weekend
Business Rule: calendar.weekend_unavailable
Type: Wyłączony
Disabled From Date: (każdy piątek)
Disabled To Date: (każda niedziela)
Active: ✓
```

**Scenariusz:** Alert tylko w godzinach pracy (9:00-17:00).

```
Name: Problem tylko w godzinach pracy
Business Rule: delivery.business_hours_issue
Type: Błąd
Disabled From Time: 17:00
Disabled To Time: 09:00
Active: ✓
```

### Tymczasowe Wyłączenie

```
Name: Znany bug w naprawie
Business Rule: cart.known_issue
Type: Do poprawy
Disabled From Date: 2026-02-20
Disabled To Date: 2026-03-01
Description: Zespół dev pracuje nad tym, pominiemy do marca
Active: ✓
```

## AlertEngine — Jak Działa

### Stare Zachowanie
```python
alert_engine.add_alert(
    rule="listing.no_products",
    title="Brak produktów",
    alert_type="bug"  # typ podany w kodzie
)
# Alert zawsze był wyświetlany
```

### Nowe Zachowanie
```python
alert_engine.add_alert(
    rule="listing.no_products",  # musi mieć config w bazie
    title="Brak produktów"
)
# Alert wyświetlony TYLKO jeśli:
# 1. Jest config dla "listing.no_products"
# 2. config.is_active = True
# 3. Nie jest w harmonogramie wyłączeń
```

## FAQ

**Q: Co się stanie z istniejącymi alertami w bazie?**
A: Pozostaną w tabeli `alerts`, ale nowe alerty będą używać nowego systemu.

**Q: Czy muszę konfigurować wszystkie alerty?**
A: Tak. Tylko skonfigurowane alerty będą wyświetlane. To celowe — daje pełną kontrolę.

**Q: Jak dodać nowy typ alertu?**
A: Bezpośrednio w bazie lub dodamy CRUD dla alert_types później.

**Q: Czy mogę mieć ten sam business_rule w różnych konfiguracjach?**
A: Nie, business_rule jest UNIQUE — jedna reguła = jedna konfiguracja.

**Q: Co jeśli alert nie ma konfiguracji?**
A: AlertEngine go ZIGNORUJE i wyloguje "nie ma konfiguracji — IGNORUJE".

## Workflow Po Migracji

1. Uruchom suite
2. Zobacz w logach: `Alert 'listing.no_products' nie ma konfiguracji — IGNORUJE`
3. Przejdź do `/alert-configs`
4. Kliknij **+ New Alert Config**
5. Wypełnij formularz
6. Uruchom suite ponownie
7. Alert się pojawi

## Nawigacja Panelu

Nowa zakładka: **Alert Configs** między Scenarios a Alerts

```
Dashboard | Runs | Scenarios | Alert Configs | Alerts | Run
```

## Checklist Migracji

- [ ] Backup bazy danych
- [ ] Nadpisanie plików
- [ ] `alembic revision --autogenerate`
- [ ] `alembic upgrade head`
- [ ] `python seed_alert_types.py`
- [ ] Restart panelu
- [ ] Sprawdzenie w `/alert-configs` czy typy są
- [ ] Dodanie pierwszej konfiguracji
- [ ] Uruchomienie testowego runu
- [ ] Sprawdzenie czy alert się pojawił
