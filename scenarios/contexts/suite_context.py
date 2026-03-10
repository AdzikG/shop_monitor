"""
SuiteContext — współdzielony kontekst dla całej suite.

Jeden egzemplarz tworzony przed startem scenariuszy, przekazywany przez:
  SuiteExecutor → ScenarioExecutor → ShopRunner → Pages / Rules

Zawiera dwa źródła danych ładowane raz przed startem suite:
  - ApiDataProvider   — dane z zewnętrznego API, odświeżane co 10 minut w tle
  - DatabaseProvider  — dane z bazy (Dictionary i inne), jednorazowy odczyt
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from sqlalchemy.orm import Session

from app.models.dictionary import Dictionary

logger = logging.getLogger(__name__)


# ── ApiDataProvider ───────────────────────────────────────────────────────────

class ApiDataProvider:
    """
    Pobiera i cache'uje dane z zewnętrznego API.

    Użycie w Pages/Rules:
        value = self.suite_context.api.get("klucz")
        all_data = self.suite_context.api.raw
    """

    REFRESH_INTERVAL = 600  # 10 minut

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout: int = 30, refresh: bool = False):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.refresh = refresh
        self._data: dict[str, Any] = {}
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Pierwsze pobranie danych + start background refresh."""
        await asyncio.to_thread(self._fetch_sync)
        if self.refresh:
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            logger.info("[ApiDataProvider] Zainicjalizowany, background refresh aktywny")
        else:
            logger.info("[ApiDataProvider] Zainicjalizowany, jednorazowy odczyt")

    async def stop(self) -> None:
        """Zatrzymuje background refresh. Wywołaj po zakończeniu suite."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("[ApiDataProvider] Zatrzymany")

    # ── Wewnętrzne ────────────────────────────────────────────────────────────

    def _fetch_sync(self) -> None:
        """Synchroniczny fetch przez requests — odpala się w osobnym wątku."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(self.api_url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            self._data = resp.json()
            if self.refresh:
                self._last_refresh = datetime.now(timezone.utc)
                logger.info(
                    f"[ApiDataProvider] Dane odświeżone o "
                    f"{self._last_refresh.strftime('%H:%M:%S')} "
                    f"({len(self._data)} kluczy)"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"[ApiDataProvider] Błąd połączenia: {e}")
            # Stare dane zostają — nie zerujemy cache
        except Exception as e:
            logger.error(f"[ApiDataProvider] Nieoczekiwany błąd: {e}")

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(self.REFRESH_INTERVAL)
            logger.debug("[ApiDataProvider] Odświeżanie danych...")
            await asyncio.to_thread(self._fetch_sync)

    # ── Publiczne metody dostępu ──────────────────────────────────────────────

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Zwraca dane z cache po ścieżce kluczy.

        Bez kluczy         → cały JSON
        Jeden klucz        → data["klucz"]
        Wiele kluczy       → data["a"]["b"]["c"]

        Przykład:
            provider.get()                        # → cały dict
            provider.get("price")                 # → data["price"]
            provider.get("data", "item", "route") # → data["data"]["item"]["route"]
        """
        if not keys:
            return self._data

        result = self._data
        for key in keys:
            if not isinstance(result, dict):
                return default
            result = result.get(key, default)
            if result is default:
                return default
        return result

    @property
    def raw(self) -> dict[str, Any]:
        """Pełny słownik danych z ostatniego fetcha."""
        return self._data

    @property
    def last_refresh(self) -> Optional[datetime]:
        """Czas ostatniego udanego pobrania."""
        return self._last_refresh

    @property
    def is_ready(self) -> bool:
        """True jeśli dane zostały pobrane przynajmniej raz."""
        return self._last_refresh is not None


# ── DatabaseProvider ──────────────────────────────────────────────────────────

class DatabaseProvider:
    """
    Ładuje dane z bazy jednorazowo przed startem suite i trzyma je w pamięci.

    Użycie w Pages/Rules:
        values = self.suite_context.db.get_dictionary("delivery")
        # → ["Kurier DPD", "InPost", "Paczkomat"]

        all_dicts = self.suite_context.db.dictionaries
        # → {"delivery": ["Kurier DPD", ...], "payment": [...], ...}
    """

    def __init__(self, db: Session):
        self._db = db
        self._dictionaries: dict[str, list[str]] = {}
        self._raw_dictionaries: dict[str, Dictionary] = {}

    def load(self) -> None:
        """Ładuje wszystkie aktywne słowniki z bazy. Wywołaj raz przed startem suite."""
        entries = (
            self._db.query(Dictionary)
            .filter(Dictionary.is_active == True)
            .order_by(Dictionary.category, Dictionary.order)
            .all()
        )

        for entry in entries:
            self._dictionaries[entry.system_name] = entry.get_values()
            self._raw_dictionaries[entry.system_name] = entry

        logger.info(
            f"[DatabaseProvider] Załadowano {len(self._dictionaries)} słowników: "
            f"{', '.join(self._dictionaries.keys())}"
        )

    def get_dictionary(self, system_name: str, default: list[str] | None = None) -> list[str]:
        """
        Zwraca listę wartości słownika po system_name.
        Zwraca default (pusta lista) jeśli słownik nie istnieje.

        Przykład:
            values = suite_context.db.get_dictionary("delivery")
            # → ["Kurier DPD", "InPost", "Paczkomat"]
        """
        return self._dictionaries.get(system_name, default if default is not None else [])

    def get_dictionary_by_category(self, category: str) -> dict[str, list[str]]:
        """
        Zwraca wszystkie słowniki z danej kategorii jako {system_name: [values]}.

        Przykład:
            suite_context.db.get_dictionary_by_category("delivery")
            # → {"delivery_courier": [...], "delivery_parcel": [...]}
        """
        return {
            name: values
            for name, entry in self._raw_dictionaries.items()
            if entry.category == category
            for values in [self._dictionaries[name]]
        }

    @property
    def dictionaries(self) -> dict[str, list[str]]:
        """Pełny słownik {system_name: [values]} wszystkich załadowanych wpisów."""
        return self._dictionaries


# ── SuiteContext ──────────────────────────────────────────────────────────────

class SuiteContext:
    """
    Współdzielony kontekst dla całej suite.

    Tworzony raz w SuiteExecutor, przekazywany do każdego scenariusza.
    Dostępny w Pages i Rules jako self.suite_context.

    Atrybuty:
        endpoints  — dict[str, ApiDataProvider] (dane z API, konfigurowane przez settings)
        db         — DatabaseProvider (dane z bazy, zawsze ładowane)

    Przykład użycia w Rules/Pages:
        # Dane z API
        price = self.suite_context.endpoints["prices"].get("product_price")

        # Dane z bazy
        delivery_options = self.suite_context.db.get_dictionary("delivery")
    """

    def __init__(self):
        self.endpoints: dict[str, ApiDataProvider] = {}
        self.db: Optional[DatabaseProvider] = None

    @classmethod
    async def initialize(
        cls,
        db: Session,
        api_endpoints: dict[str, dict] | None = None,
        timeout: int = 30,
    ) -> "SuiteContext":
        """
        api_endpoints: {
            "nazwa": {
                "url":     "https://...",
                "key":     "token",        # opcjonalne
                "refresh": True/False      # opcjonalne, domyślnie False
            }
        }
        """
        instance = cls()

        instance.db = DatabaseProvider(db=db)
        instance.db.load()

        if api_endpoints:
            for name, config in api_endpoints.items():
                provider = ApiDataProvider(
                    api_url=config["url"],
                    api_key=config.get("key"),
                    timeout=timeout,
                    refresh=config.get("refresh", False),
                )
                await provider.initialize()
                instance.endpoints[name] = provider

        return instance

    async def teardown(self) -> None:
        """Zatrzymuje background refresh wszystkich endpointów. Wywołaj w finally SuiteExecutor."""
        for name, provider in self.endpoints.items():
            await provider.stop()
            logger.debug(f"[SuiteContext] Endpoint '{name}' zatrzymany")
