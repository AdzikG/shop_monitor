# Rules — logika biznesowa

Plik opisuje architekturę warstwy reguł: `BaseRules`, `RulesResult`, wzorzec instructions oraz wszystkie konkretne klasy reguł.

**Zasada:** Pages nigdy nie oceniają poprawności danych — to zadanie Rules. Rules nigdy nie dotykają przeglądarki — to zadanie Pages.

---

## BaseRules (`scenarios/rules/base_rules.py`)

```python
class BaseRules:
    def __init__(self, context: ScenarioContext): ...
    def check(self, run_data: RunData) -> RulesResult: ...  # do nadpisania
```

### Metody fabryczne

#### `alert(business_rule, description="", alert_type="bug") → AlertResult`

Tworzy `AlertResult` — nie zapisuje do DB, nie zgłasza nic. Tylko buduje obiekt.

```python
self.alert('CART1_DELIVERY_UNAVAILABLE', f'Dostawa "{name}" niedostępna')
self.alert('PRODUCT_UNAVAILABLE', 'Produkt niedostępny', alert_type='to_verify')
```

#### `ok(alerts=None, instructions=None) → RulesResult`

Test kontynuuje dalej. Użyj gdy:
- brak alertów: `return self.ok()`
- alerty ale test idzie dalej: `return self.ok(alerts=alerts)`
- instrukcje dla kolejnego etapu: `return self.ok(instructions={...})`
- oba: `return self.ok(alerts=alerts, instructions={...})`

#### `stop(alerts, reason, instructions=None) → RulesResult`

Zatrzymaj test — ShopRunner złapie `RulesResult.should_stop=True` i rzuci `StopTest`. Użyj gdy brak danych/możliwości do kontynuowania:
- pusty koszyk
- brak wymaganej dostawy
- brak wymaganej płatności
- krytyczny błąd strony

---

## RulesResult (`scenarios/rules_result.py`)

```python
@dataclass
class RulesResult:
    alerts: list[AlertResult] = field(default_factory=list)
    should_stop: bool = False
    stop_reason: str = ""
    instructions: dict = field(default_factory=dict)
```

| Pole | Typ | Opis |
|---|---|---|
| `alerts` | `list[AlertResult]` | Alerty zebranne w tym etapie |
| `should_stop` | `bool` | True = ShopRunner rzuci `StopTest` |
| `stop_reason` | `str` | Powód zatrzymania (logowany) |
| `instructions` | `dict` | Dyspozycje dla kolejnych etapów |

---

## AlertResult (`scenarios/rules_result.py`)

```python
@dataclass
class AlertResult:
    business_rule: str       # np. "CART1_DELIVERY_UNAVAILABLE"
    description: str = ""   # szczegółowy opis (np. co było dostępne)
    alert_type: str = "bug"  # slug: bug / to_verify / to_improve / disabled
```

`business_rule` musi mieć odpowiadający `AlertConfig` w DB — inaczej alert jest cicho ignorowany.

---

## Wzorzec `instructions`

Instructions to słownik przekazywany do kolejnych Pages. Rules jednego etapu mogą poinformować następne Pages o kontekście:

```python
# Cart0Rules przekazuje do Cart1Page, Cart2Page, ...
instructions['requires_postal_code'] = True    # dostawa wymaga kodu
instructions['fill_company_fields'] = True     # formularz firmowy

# ListingPage może umieścić w instructions:
# (przez forced_listing_url z retry)
instructions['forced_listing_url'] = 'https://...'
```

**Ważne:** Instructions są akumulowane przez cały test — `ShopRunner._process_result()` wywołuje `self.instructions.update(result.instructions)`. Kolejne etapy mogą nadpisywać klucze.

Każdy Page odbiera instructions jako argument `execute(instructions: dict)` i może z nich korzystać lub je ignorować.

---

## HomeRules (`scenarios/rules/home_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `run_data.home` jest `None` lub `not loaded` | `HOME_NOT_LOADED` | `stop()` |

**Kiedy stop():** Strona główna nie załadowała się — nie ma sensu kontynuować.

---

## ListingRules (`scenarios/rules/listing_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `run_data.listing` jest `None` lub `not available` | `PRODUCT_UNAVAILABLE` (type: `to_verify`) | `stop()` |

**Kiedy stop():** Produkt niedostępny — nie można dodać do koszyka.

---

## Cart0Rules (`scenarios/rules/cart0_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `cart0` jest `None` lub `item_count == 0` | `CART0_EMPTY` | `stop()` |
| `cart0.total_price is None` | `CART0_NO_PRICE` (type: `to_verify`) | kontynuuje |

**Instructions generowane przez Cart0Rules:**

```python
# Jeśli dostawa to Kurier / Kurier jutro / Kurier 48h:
instructions['requires_postal_code'] = True

# Jeśli flaga 'company_address' aktywna:
instructions['fill_company_fields'] = True
```

---

## Cart1Rules (`scenarios/rules/cart1_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `context.delivery_name` nie ma na liście dostępnych | `CART1_DELIVERY_UNAVAILABLE` | `stop()` |
| Dostawa była na liście ale `cart1.selected` jest None | `CART1_DELIVERY_NOT_SELECTED` | `stop()` |
| `postal_code_required` ale `not postal_code_filled` | `CART1_POSTAL_CODE_MISSING` (type: `config`) | `stop()` |
| `cutoff_time != context.delivery_cutoff` | `CART1_CUTOFF_MISMATCH` (type: `to_verify`) | kontynuuje |

**Uwaga:** `CART1_POSTAL_CODE_MISSING` ma `alert_type='config'` — oznacza błąd konfiguracji scenariusza (brak kodu pocztowego), nie błąd sklepu.

---

## Cart2Rules (`scenarios/rules/cart2_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `context.payment_name` nie ma na liście dostępnych | `CART2_PAYMENT_UNAVAILABLE` | `stop()` |
| Płatność była na liście ale `cart2.selected` jest None | `CART2_PAYMENT_NOT_SELECTED` | `stop()` |

---

## Cart3Rules (`scenarios/rules/cart3_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `cart3.postal_code != context.postal_code` | `CART3_POSTAL_MISMATCH` (type: `to_verify`) | kontynuuje |

---

## Cart4Rules (`scenarios/rules/cart4_rules.py`)

| Warunek | Alert | Akcja |
|---|---|---|
| `cart4.total_price != cart0.total_price + cart1.price` (tolerancja 0.01) | `CART4_PRICE_MISMATCH` | kontynuuje |
| `context.delivery_name not in cart4.delivery_name` | `CART4_DELIVERY_MISMATCH` | kontynuuje |
| `context.payment_name not in cart4.payment_name` | `CART4_PAYMENT_MISMATCH` | kontynuuje |

Cart4Rules nigdy nie wywołuje `stop()` — raportuje rozbieżności ale test uznaje za zakończony.

---

## GlobalRules (`scenarios/rules/global_rules.py`)

Wywoływane **po wszystkich etapach** przez `ShopRunner.run()` — mają dostęp do danych ze wszystkich etapów przez `run_data`.

| Warunek | Alert | Akcja |
|---|---|---|
| `listing.price != cart0.total_price` (tolerancja 0.01) | `GLOBAL_PRICE_CHANGED` | kontynuuje |

**Zastosowanie:** Porównania cross-stage, które wymagają danych z wielu etapów jednocześnie.

---

## Jak dodać nową regułę

### W istniejącym pliku rules

```python
# scenarios/rules/cart0_rules.py
class Cart0Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        ...
        # Dodaj nowy warunek:
        if cart0.item_count > 10:
            alerts.append(self.alert(
                'CART0_TOO_MANY_ITEMS',
                f'Koszyk zawiera {cart0.item_count} pozycji',
                alert_type='to_verify',
            ))
        return self.ok(alerts=alerts)
```

### Nowy `business_rule` → widoczny alert

1. Dodaj warunek w odpowiednich Rules (kod powyżej)
2. W panelu przejdź do `/alert-configs` → "Dodaj konfigurację"
3. Wpisz dokładnie tę samą wartość `business_rule` (np. `CART0_TOO_MANY_ITEMS`)
4. Wybierz `AlertType` (bug/to_verify/to_improve/disabled)
5. Zapisz — od teraz alerty będą widoczne

Bez kroku 2–5 alert jest cicho ignorowany przez `AlertEngine`.

### Nowa klasa Rules (nowy etap)

Patrz [HOW_TO_EXTEND.md](HOW_TO_EXTEND.md).
