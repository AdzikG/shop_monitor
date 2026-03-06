# Jak dodawać, zmieniać i usuwać kolumny w modelach

Instrukcja krok po kroku dla SQLAlchemy + Alembic (SQLite/MySQL).

---

## Zasada ogólna

Każda zmiana w modelu (`app/models/*.py`) wymaga wygenerowania i zastosowania migracji Alembic.
Nigdy nie edytuj bazy ręcznie — zawsze idź przez migrację.

```
model .py  →  alembic autogenerate  →  alembic upgrade head
```

---

## 1. Dodanie nowej kolumny

### a) Edytuj model

```python
# app/models/example.py
class Example(Base):
    ...
    new_field: Mapped[str] = mapped_column(String(100), nullable=False, default="")
```

**Ważne dla SQLite** — jeśli kolumna jest `nullable=False`, musisz dodać `server_default`:

```python
new_field: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
```

Bez `server_default` SQLite rzuci błąd przy `alembic upgrade` dla istniejącej tabeli z danymi.

### b) Wygeneruj i zastosuj migrację

```bash
alembic revision --autogenerate -m "add new_field to example"
alembic upgrade head
```

### c) Sprawdź wygenerowany plik migracji

```
alembic/versions/<hash>_add_new_field_to_example.py
```

Upewnij się, że `op.add_column` zawiera `server_default=''` jeśli kolumna jest NOT NULL:

```python
op.add_column('example', sa.Column('new_field', sa.String(100), nullable=False, server_default=''))
```

---

## 2. Zmiana istniejącej kolumny

### a) Zmień definicję w modelu

Przykład — zmiana długości stringa ze 100 na 255:

```python
# przed
name: Mapped[str] = mapped_column(String(100), nullable=False)

# po
name: Mapped[str] = mapped_column(String(255), nullable=False)
```

Przykład — usunięcie `unique=True`:

```python
# przed
name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

# po
name: Mapped[str] = mapped_column(String(50), nullable=False)
```

### b) Wygeneruj i zastosuj migrację

```bash
alembic revision --autogenerate -m "alter example name length"
alembic upgrade head
```

### Uwaga — SQLite i `ALTER COLUMN`

SQLite nie obsługuje `ALTER COLUMN`. Alembic w trybie `render_as_batch=True` (skonfigurowanym w tym projekcie) automatycznie wykonuje sekwencję:

1. Utwórz tymczasową tabelę z nową strukturą
2. Skopiuj dane
3. Usuń starą tabelę
4. Zmień nazwę tymczasowej

Dzieje się to automatycznie — nie musisz nic robić.

---

## 3. Usunięcie kolumny

### a) Usuń pole z modelu

```python
# usuń tę linię:
login: Mapped[str | None] = mapped_column(String(255))
```

Jeśli kolumna była importowana gdzie indziej (np. w seed.py, kontekście), usuń te referencje.

### b) Sprawdź referencje

```bash
grep -r "login" app/ scenarios/ seed.py
```

### c) Wygeneruj i zastosuj migrację

```bash
alembic revision --autogenerate -m "drop login from example"
alembic upgrade head
```

---

## 4. Zmiana constraintów (unique, index, nullable)

### Dodanie `unique=True`

```python
name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
```

```bash
alembic revision --autogenerate -m "add unique to example name"
alembic upgrade head
```

### Usunięcie `unique=True`

```python
name: Mapped[str] = mapped_column(String(50), nullable=False)
```

```bash
alembic revision --autogenerate -m "drop unique from example name"
alembic upgrade head
```

### Dodanie indeksu

```python
from sqlalchemy import Index

class Example(Base):
    ...
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
```

---

## 5. Dodanie nowego modelu (nowej tabeli)

1. Utwórz plik `app/models/new_table.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class NewTable(Base):
    __tablename__ = "new_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
```

2. Dodaj import do `app/models/__init__.py`:

```python
from app.models.new_table import NewTable
```

3. Wygeneruj i zastosuj migrację:

```bash
alembic revision --autogenerate -m "add new_table"
alembic upgrade head
```

---

## 6. Przydatne komendy Alembic

```bash
alembic current          # pokaż aktualną wersję bazy
alembic history          # historia migracji
alembic upgrade head     # zastosuj wszystkie migracje
alembic downgrade -1     # cofnij ostatnią migrację
alembic upgrade +1       # zastosuj jedną migrację do przodu
```

---

## 7. Typowe błędy

| Błąd | Przyczyna | Rozwiązanie |
|------|-----------|-------------|
| `Cannot add a NOT NULL column with default value NULL` | SQLite, brak `server_default` | Dodaj `server_default=''` w pliku migracji |
| `Target database is not up to date` | Niezastosowane migracje | `alembic upgrade head` |
| `Can't locate revision` | Usunięty plik migracji | Sprawdź `alembic/versions/` |
| Autogenerate nie wykrywa zmian | Brak importu modelu w `app/models/__init__.py` | Dodaj import |

---

## Schemat działania — ściągawka

```
1. Edytuj app/models/*.py
2. alembic revision --autogenerate -m "opis zmiany"
3. Sprawdź wygenerowany plik w alembic/versions/
4. alembic upgrade head
5. alembic current  ← potwierdź że wskazuje na head
```
