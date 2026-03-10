"""
List helpers — operacje na listach i kolekcjach.
"""


def find_missing(expected: list[str], available: list[str]) -> list[str]:
    """
    Zwraca elementy z expected których nie ma w available.

    Przykład:
        find_missing(["Kurier", "Paczkomat"], ["Kurier"]) → ["Paczkomat"]
    """
    available_set = set(available)
    return [item for item in expected if item not in available_set]


def find_matching(name: str, options: list[str], case_sensitive: bool = False) -> str | None:
    """
    Szuka pierwszego dopasowania nazwy na liście opcji.
    Domyślnie porównuje bez uwzględniania wielkości liter.

    Przykład:
        find_matching("kurier", ["Kurier", "Paczkomat"]) → "Kurier"
    """
    if case_sensitive:
        return name if name in options else None
    name_lower = name.lower()
    for option in options:
        if option.lower() == name_lower:
            return option
    return None


def deduplicate(items: list) -> list:
    """Usuwa duplikaty zachowując kolejność."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten(nested: list[list]) -> list:
    """Spłaszcza listę list do jednej listy."""
    return [item for sublist in nested for item in sublist]


def first_or_none(items: list):
    """Zwraca pierwszy element listy lub None jeśli lista pusta."""
    return items[0] if items else None
