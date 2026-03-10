"""
Config — centralna konfiguracja aplikacji.

Wartości są czytane ze zmiennych środowiskowych lub pliku .env.
Dostęp przez singleton: from core.config import settings
"""

import os
from pathlib import Path
from typing import TypedDict, Literal
from dotenv import load_dotenv

# Szukaj .env w katalogu głównym projektu
load_dotenv(Path(__file__).parent.parent / ".env")


def _get(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Wymagana zmienna środowiskowa nie jest ustawiona: {key}")
    return value

class TestAccount(TypedDict):
    login: str
    password: str

# Dostępne nazwy kont testowych — dopisz tutaj gdy dodajesz nowe konto w .env
TestAccountName = Literal["admin", "user"]

class Settings:
    """
    Konfiguracja aplikacji czytana ze zmiennych środowiskowych / .env

    Sekcje:
        Baza danych       — DATABASE_*
        Aplikacja         — APP_*
        API zewnętrzne    — API_*
    """

    # ── Baza danych ───────────────────────────────────────────────────────────

    @property
    def database_url(self) -> str:
        return _get("DATABASE_URL", "sqlite:///./shop_monitor.db")

    # ── Aplikacja ─────────────────────────────────────────────────────────────

    @property
    def app_host(self) -> str:
        return _get("APP_HOST", "0.0.0.0")

    @property
    def app_port(self) -> int:
        return int(_get("APP_PORT", "8000"))


    # ── API zewnętrzne ────────────────────────────────────────────────────────
    #
    # Konwencja nazw:
    #   API_<NAZWA>_URL    — adres endpointu
    #   API_<NAZWA>_TOKEN  — Bearer token (jeśli wymagany)
    #   API_<NAZWA>_KEY    — klucz API (jeśli inny mechanizm auth)
    #
    # Przykład dla dwóch endpointów:
    #   API_PRICES_URL=https://api.example.com/prices
    #   API_PRICES_TOKEN=secret123
    #   API_CONFIG_URL=https://api.example.com/config

    @property
    def api_prices_url(self) -> str | None:
        return _get("API_PRICES_URL")

    @property
    def api_prices_token(self) -> str | None:
        return _get("API_PRICES_TOKEN")

    @property
    def api_config_url(self) -> str | None:
        return _get("API_CONFIG_URL")

    @property
    def api_config_token(self) -> str | None:
        return _get("API_CONFIG_TOKEN")
    
    @property
    def api_gethub_url(self) -> str | None:
        return _get("API_GETHUB_URL")

    @property
    def api_gethub_token(self) -> str | None:
        return _get("API_GETHUB_TOKEN")

    # ── Helper: buduje api_endpoints dla SuiteContext ─────────────────────────

    def build_api_endpoints(self) -> dict[str, dict]:
        """
        Buduje słownik endpointów dla SuiteContext.initialize().
        Pomija endpointy bez skonfigurowanego URL.

        Zwraca:
            {
                "prices": {"url": "...", "key": "...", "refresh": True},
                "config": {"url": "...", "refresh": False},
            }
        """
        endpoints = {}

        if self.api_prices_url:
            endpoints["prices"] = {
                "url":     self.api_prices_url,
                "key":     self.api_prices_token,
                "refresh": True,   # odświeżany co 10 min w tle
            }

        if self.api_config_url:
            endpoints["config"] = {
                "url":     self.api_config_url,
                "key":     self.api_config_token,
                "refresh": False,  # jednorazowy odczyt
            }
        if self.api_gethub_url:
            endpoints["gethub"] = {
                "url":     self.api_gethub_url,
                "key":     self.api_gethub_token,
                "refresh": False,  # jednorazowy odczyt
            }

        return endpoints
    

    # ── Helper: przekazuje dane logowania na podstawie nazwy klucza ─────────────────────────
    
    def get_test_account(self, name: TestAccountName, environment: str | None = None) -> TestAccount | None:
        """
        Zwraca konto testowe po nazwie zdefiniowanej w .env.

        Konwencja nazw w .env:
            Bez środowiska:   TEST_ACCOUNT_<NAZWA>_LOGIN / _PASS
            Ze środowiskiem:  TEST_ACCOUNT_<ŚRODOWISKO>_<NAZWA>_LOGIN / _PASS

        Przykład .env:
            TEST_ACCOUNT_ADMIN_LOGIN=jan@example.com
            TEST_ACCOUNT_ADMIN_PASS=haslo123

            TEST_ACCOUNT_PROD_ADMIN_LOGIN=jan@prod.example.com
            TEST_ACCOUNT_PROD_ADMIN_PASS=haslo456

        Zwraca None jeśli konto nie jest skonfigurowane w .env.
        """
        prefix = f"TEST_ACCOUNT_{environment.upper()}_{name.upper()}" if environment else f"TEST_ACCOUNT_{name.upper()}"
        login    = _get(f"{prefix}_LOGIN")
        password = _get(f"{prefix}_PASS")
        if not login or not password:
            return None
        return TestAccount(login=login, password=password)


# Singleton — importuj to w całym projekcie
settings = Settings()
