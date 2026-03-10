"""
String helpers — operacje na tekstach i listach.
"""


def join_lines(items: list[str]) -> str:
    """Łączy listę stringów znakiem nowej linii."""
    return "\n".join(items)


def join_comma(items: list[str]) -> str:
    """Łączy listę stringów przecinkiem i spacją."""
    return ", ".join(items)


def normalize_whitespace(text: str) -> str:
    """Usuwa nadmiarowe spacje i znaki niedrukowalne."""
    return " ".join(text.split())


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Obcina tekst do max_length znaków z sufiksem."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def is_empty(text: str | None) -> bool:
    """True jeśli tekst jest None, pusty lub zawiera tylko białe znaki."""
    return not text or not text.strip()


def extract_first_line(text: str) -> str:
    """Zwraca pierwszą niepustą linię tekstu."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
