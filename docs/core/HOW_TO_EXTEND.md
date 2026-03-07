# Jak rozwijać projekt (How to Extend)

Przewodniki krok po kroku dla najczęstszych zadań rozszerzania systemu.

---

## 1. Nowy etap (page + rules + RunData)

Przykład: dodanie etapu `upsell` między Cart0 a Cart1.

### Krok 1 — Nowy data class w RunData

```python
# scenarios/run_data.py
@dataclass
class UpsellData:
    shown: bool = False
    accepted: bool = False
    added_price: Optional[float] = None

@dataclass
class RunData:
    ...
    upsell: Optional[UpsellData] = None  # dodaj pole
```

### Krok 2 — Nowy Page

```python
# scenarios/pages/upsell_page.py
from scenarios.pages.base_page import BasePage, Sel
from scenarios.run_data import UpsellData

class UpsellPage(BasePage):

    class Modal:
        SECTION  = Sel(desktop=('locator', '.upsell-modal'))
        BTN_YES  = Sel(desktop=('role', 'button', {'name': 'Tak, dodaj'}))
        BTN_SKIP = Sel(desktop=('role', 'button', {'name': 'Nie, dziękuję'}))
        PRICE    = Sel(desktop=('locator', '.upsell-price'))

    async def execute(self, instructions: dict) -> UpsellData:
        await self.wait_for_navigation()

        shown = await self.is_visible(self.Modal.SECTION)
        accepted = False
        added_price = None

        if shown:
            added_price = await self.get_decimal(self.Modal.PRICE)
            # logika akceptacji/pominięcia
            await self.sloc(self.Modal.BTN_SKIP).click()
            await self.wait_for_navigation()

        return UpsellData(shown=shown, accepted=accepted, added_price=added_price)
```

### Krok 3 — Nowe Rules

```python
# scenarios/rules/upsell_rules.py
from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules

class UpsellRules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        upsell = run_data.upsell
        alerts = []

        if upsell and not upsell.shown and self.context.flag('expects_upsell'):
            alerts.append(self.alert(
                'UPSELL_NOT_SHOWN',
                'Upsell powinien być wyświetlony ale nie był',
                alert_type='to_verify',
            ))

        return self.ok(alerts=alerts)
```

### Krok 4 — Eksport z `__init__.py`

```python
# scenarios/pages/__init__.py
from .upsell_page import UpsellPage

# scenarios/rules/__init__.py
from .upsell_rules import UpsellRules
```

### Krok 5 — Dodanie do ShopRunner

```python
# scenarios/shop_runner.py
from scenarios.pages import ..., UpsellPage
from scenarios.rules import ..., UpsellRules

async def run(self) -> ShopRunResult:
    ...
    await self._run_cart0()
    await self._run_upsell()    # nowy etap
    if self.context.is_order:
        await self._run_cart1()
    ...

async def _run_upsell(self):
    self._current_stage = 'Upsell'
    self.run_data.upsell = await self._get_page(UpsellPage).execute(self.instructions)
    await self._screenshot('upsell')
    self._process_result(UpsellRules(self.context).check(self.run_data), 'upsell')
```

---

## 2. Nowa reguła biznesowa w istniejącym etapie

### Krok 1 — Dodaj warunek w Rules

```python
# scenarios/rules/cart0_rules.py
class Cart0Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart0 = run_data.cart0
        alerts = []

        # ... istniejące warunki ...

        # Nowy warunek:
        if cart0.total_price and cart0.total_price > 10000:
            alerts.append(self.alert(
                'CART0_SUSPICIOUSLY_HIGH_PRICE',
                f'Cena {cart0.total_price} jest podejrzanie wysoka',
                alert_type='to_verify',
            ))

        return self.ok(alerts=alerts, instructions=instructions)
```

### Krok 2 — Opcjonalnie: zbierz potrzebne dane w Page

Jeśli reguła potrzebuje danych których Page jeszcze nie zbiera — najpierw rozszerz data class i Page (patrz przewodnik 1).

### Krok 3 — Utwórz AlertConfig w panelu

W panelu przejdź do `/alert-configs` → "Dodaj konfigurację":
- `business_rule`: `CART0_SUSPICIOUSLY_HIGH_PRICE`
- `name`: np. "Podejrzanie wysoka cena w koszyku"
- `alert_type`: wybierz `to_verify`

Bez tego kroku alert jest **cicho ignorowany**.

---

## 3. Nowy business_rule → widoczny alert (tylko konfiguracja)

Gdy kod reguły już istnieje, ale alert nie pojawia się w UI:

1. Otwórz `/alert-configs`
2. Kliknij "Dodaj konfigurację"
3. Wypełnij:
   - `business_rule` — **dokładnie** tak jak w kodzie (case-sensitive)
   - `name` — tytuł w UI
   - `alert_type` — bug/to_verify/to_improve/disabled
4. Zapisz

Alert zacznie się pojawiać od następnego runu.

---

## 4. Nowy model DB

### Krok 1 — Utwórz model

```python
# app/models/product_blacklist.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from app.models.base import Base, now_utc

class ProductBlacklist(Base):
    __tablename__ = "product_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    url_pattern: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[DateTime] = mapped_column(default=now_utc)
```

### Krok 2 — Import w `__init__.py`

```python
# app/models/__init__.py
from .product_blacklist import ProductBlacklist
```

### Krok 3 — Migracja Alembic

```bash
alembic revision --autogenerate -m "add product_blacklist"
alembic upgrade head
```

### Krok 4 — (opcjonalnie) Router CRUD

Utwórz `app/routers/product_blacklist.py` i zarejestruj w `app/main.py`:

```python
# app/main.py
from app.routers import product_blacklist
app.include_router(product_blacklist.router)
```

---

## 5. Nowy argument CLI (`main.py`)

```python
# main.py
def parse_args():
    parser = argparse.ArgumentParser()
    ...
    # Dodaj nowy argument:
    parser.add_argument('--dry-run', action='store_true',
                        help='Uruchom bez zapisywania do bazy')
    return parser.parse_args()

# Użyj w kodzie:
args = parse_args()
if args.dry_run:
    ...
```

---

## 6. Nowy router w panelu

### Krok 1 — Utwórz router

```python
# app/routers/my_feature.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(prefix="/my-feature", tags=["my-feature"])
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def list_view(request: Request, db: Session = Depends(get_db)):
    items = db.query(...).all()
    return templates.TemplateResponse(
        "my_feature/index.html",
        {"request": request, "items": items}
    )
```

### Krok 2 — Zarejestruj w `app/main.py`

```python
from app.routers import my_feature
app.include_router(my_feature.router)
```

### Krok 3 — Utwórz szablon

```
app/templates/my_feature/index.html
```

Szablon dziedziczy z `base.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>My Feature</h1>
{% for item in items %}
    <p>{{ item.name }}</p>
{% endfor %}
{% endblock %}
```

### Krok 4 — (opcjonalnie) Link w nawigacji

Dodaj link do `app/templates/base.html` w sekcji nawigacji.

---

## Checklist po każdej zmianie

### Nowy business_rule
- [ ] Warunek w Rules
- [ ] AlertConfig w panelu `/alert-configs`
- [ ] Test manualny (uruchom scenariusz gdzie warunek jest spełniony)

### Nowy model DB
- [ ] `app/models/new.py`
- [ ] Import w `app/models/__init__.py`
- [ ] `alembic revision --autogenerate -m "..."`
- [ ] `alembic upgrade head`

### Nowy etap (page + rules)
- [ ] Data class w `run_data.py`
- [ ] Page w `scenarios/pages/`
- [ ] Rules w `scenarios/rules/`
- [ ] Eksport z `__init__.py` obu modułów
- [ ] Metoda `_run_X()` w `ShopRunner`
- [ ] Wywołanie w `ShopRunner.run()`
- [ ] AlertConfig dla każdego nowego business_rule
