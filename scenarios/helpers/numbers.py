"""
Number helpers — parsowanie kwot i operacje liczbowe.
"""
import re
import logging

logger = logging.getLogger(__name__)


def parse_amount(value: str) -> float | None:
    """
    Parsuje string z kwotą na float.
    Obsługuje złotówki, spacje, przecinki i myślniki.

    Przykłady:
        "123,45 zł"  → 123.45
        "1 234,56"   → 1234.56
        "-50,00 zł"  → -50.0
        "brak"       → None
    """
    if not value:
        return None
    cleaned = re.sub(r'[^\d\-,]', '', value).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        logger.debug(f"[parse_amount] Cannot parse: '{value}'")
        return None


def sum_amounts(amounts: list[str]) -> float:
    """
    Sumuje listę stringów z kwotami.
    Pomija wartości których nie można sparsować.

    Przykład:
        ["123,45 zł", "56,55 zł", "brak"] → 180.0
    """
    total = 0.0
    for raw in amounts:
        value = parse_amount(raw)
        if value is not None:
            total += value
        else:
            logger.warning(f"[sum_amounts] Skipped unparseable value: '{raw}'")
    return round(total, 2)


def amounts_match(total_str: str, expected: float, tolerance: float = 0.01) -> bool:
    """
    Sprawdza czy sparsowana kwota zgadza się z oczekiwaną wartością.
    Tolerancja domyślnie 1 grosz — zabezpieczenie przed błędami zaokrągleń.

    Przykład:
        amounts_match("180,00 zł", 180.0) → True
        amounts_match("179,99 zł", 180.0) → False
    """
    parsed = parse_amount(total_str)
    if parsed is None:
        return False
    return abs(parsed - expected) <= tolerance


def format_amount(value: float) -> str:
    """Formatuje float jako czytelną kwotę z dwoma miejscami po przecinku."""
    return f"{value:.2f}"
