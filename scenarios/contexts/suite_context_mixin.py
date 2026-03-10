from __future__ import annotations
from typing import TYPE_CHECKING
from core.config import settings, TestAccountName, TestAccount

if TYPE_CHECKING:
    from scenarios.contexts.suite_context import SuiteContext
    from scenarios.contexts.scenario_context import ScenarioContext


class SuiteContextMixin:
    """
    Mixin dostarczający helpery dostępu do SuiteContext.
    Używany przez BasePage i BaseRules.

    Wymaga żeby klasa dziedzicząca miała atrybut self.suite_context.
    """

    suite_context: "SuiteContext | None"
    scenario_context: "ScenarioContext | None"

    def get_api(self, endpoint: str, *keys: str, default=None):
        """
        Zwraca dane z endpointu API.

        Bez kluczy         → cały JSON z endpointu
        Jeden klucz        → data["klucz"]
        Wiele kluczy       → data["a"]["b"]["c"]

        Przykład:
            self.get_api("prices")                          # → cały dict
            self.get_api("prices", "product_123")           # → data["product_123"]
            self.get_api("config", "data", "item", "route") # → data["data"]["item"]["route"]
        """
        if not self.suite_context:
            return default
        provider = self.suite_context.endpoints.get(endpoint)
        if not provider:
            return default
        return provider.get(*keys, default=default)

    def get_dictionary(self, system_name: str, default: list[str] | None = None) -> list[str]:
        """
        Zwraca listę wartości słownika z bazy po system_name.
        Zwraca default (pusta lista) jeśli suite_context niedostępny lub słownik nie istnieje.

        Przykład:
            delivery_options = self.get_dictionary("delivery")
            payment_options  = self.get_dictionary("payment")
        """
        if not self.suite_context or not self.suite_context.db:
            return default if default is not None else []
        return self.suite_context.db.get_dictionary(system_name, default)
    
    def get_test_account(self, name: TestAccountName) -> TestAccount | None:
        """
        Zwraca konto testowe po nazwie zdefiniowanej w .env.

        Przykład:
            account = self.get_test_account("admin")
            if account:
                await self.safe_fill(self.LOGIN, account["login"])
                await self.safe_fill(self.PASS,  account["password"])
        """
        env_name = self.scenario_context.environment_name if self.scenario_context else None
        return settings.get_test_account(name, env_name)
