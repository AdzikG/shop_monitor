# Refactor Alertów — Instrukcja Migracji

## Co się zmienia?

### Przed
- Każdy suite_run tworzy nowe alert_groups
- Duplikaty: ten sam alert w run #1, #2, #3 → 3 wpisy w bazie
- Brak informacji o powtórzeniach

### Po
- Alert deduplikuje się jeśli powtarza (te same scenario_ids + środowisko)
- Licznik `repeat_count` pokazuje ile razy wystąpił
- Historia suite_runs w `suite_run_history`

## Nowe pola w AlertGroup

```python
last_suite_run_id      # FK do ostatniego suite_run
suite_run_history      # JSON: [1, 5, 12] — historia wszystkich runów
repeat_count           # ile razy powtórzył się alert
first_seen_at          # kiedy pierwszy raz
last_seen_at           # kiedy ostatnio
```

## Kroki Migracji

### 1. Backup bazy

```bash
copy shop_monitor.db shop_monitor_backup_$(date +%Y%m%d).db
```

### 2. Nadpisz pliki

- `app/models/alert_group.py` — nowa struktura
- `scenarios/suite_executor.py` — logika deduplikacji
- `app/routers/alerts.py` — nowy widok z filtrami
- `app/templates/alerts_list.html` — nowy szablon
- `app/templates.py` — filtr parse_json

### 3. Wygeneruj migrację

```bash
alembic revision --autogenerate -m "alerts refactor with deduplication"
```

### 4. **RĘCZNIE EDYTUJ** migrację

Alembic wygeneruje dodanie kolumn, ale trzeba dodać wartości domyślne dla istniejących rekordów:

```python
def upgrade():
    # Dodaj nowe kolumny
    with op.batch_alter_table('alert_groups') as batch_op:
        batch_op.add_column(sa.Column('last_suite_run_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('suite_run_history', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('repeat_count', sa.Integer(), server_default='1'))
        batch_op.add_column(sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    
    # Wypełnij wartości domyślne dla istniejących rekordów
    op.execute("""
        UPDATE alert_groups 
        SET 
            last_suite_run_id = suite_run_id,
            suite_run_history = json_array(suite_run_id),
            repeat_count = 1,
            first_seen_at = datetime('now'),
            last_seen_at = datetime('now')
        WHERE last_suite_run_id IS NULL
    """)
    
    # Teraz ustaw NOT NULL
    with op.batch_alter_table('alert_groups') as batch_op:
        batch_op.alter_column('last_suite_run_id', nullable=False)
        batch_op.create_foreign_key('fk_alert_groups_last_suite_run', 
                                      'suite_runs', ['last_suite_run_id'], ['id'])
```

### 5. Zastosuj migrację

```bash
alembic upgrade head
```

### 6. Restart panelu

```bash
python run_panel.py
```

## Jak działa deduplikacja?

### Przykład

**Run #1** — Elektronika failuje na "listing.no_products", scenario_ids=[1,2]
→ Tworzy AlertGroup (repeat_count=1)

**Run #2** — Elektronika failuje NA TYM SAMYM, scenario_ids=[1,2]
→ Znajduje istniejący AlertGroup → repeat_count=2

**Run #3** — Elektronika failuje ale scenario_ids=[1,3] (inny scenariusz)
→ Nowy AlertGroup (inne scenariusze)

### Warunki deduplikacji

Alert deduplikuje się jeśli:
1. `business_rule` ten sam
2. `scenario_ids` dokładnie te same (sorted)
3. `environment_id` ten sam
4. Status `open` lub `in_progress` (zamknięte nie deduplikują)

## Nowy widok /alerts

### Filtry
- **Status:** Active / Closed / All
- **Environment:** RC / PROD / All
- **Search:** po title lub business_rule

### Kolumny
- Last Seen (+ badge z repeat_count jeśli >1)
- Type (bug, to_verify)
- Title (+ "Repeated X times")
- Suite (link do suite_run)
- Environment
- Scenarios (linki do #1 #2 #3 z occurrence_count)
- Status
- Actions (Start / Close)

### Ukryte
- Business Rule (zbędne, jest title)
- Count (przeniesione do scenario links)

## Testowanie

```bash
# Uruchom suite 2 razy z rzędu
python main.py --suite 1 --environment 1
python main.py --suite 1 --environment 1

# Sprawdź w /alerts czy ten sam alert ma repeat_count=2
```

## Rollback

Jeśli coś pójdzie nie tak:

```bash
# Przywróć backup
copy shop_monitor_backup_*.db shop_monitor.db

# Lub cofnij migrację
alembic downgrade -1
```

## Troubleshooting

**Problem:** Foreign key constraint failed
**Fix:** Upewnij się że `last_suite_run_id` wskazuje na istniejący suite_run

**Problem:** JSON parse error
**Fix:** Sprawdź czy `suite_run_history` to poprawny JSON: `[1,2,3]`

**Problem:** Alerty się nie deduplikują
**Debug:** Sprawdź w logach czy `scenario_ids` są identyczne (sorted!)
