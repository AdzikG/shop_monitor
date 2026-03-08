from scenarios.context import ScenarioContext
from scenarios.run_data import RunData
from scenarios.rules_result import AlertResult, RulesResult


class BaseRules:
    def __init__(self, context: ScenarioContext):
        self.context = context
        self._alerts: list[AlertResult] = []

    def check(self, run_data: RunData) -> RulesResult:
        raise NotImplementedError

    def add_alert(self, business_rule: str, description: str = "") -> None:
        """Dodaje alert do kolejki. Wywołaj przed ok() lub stop()."""
        self._alerts.append(AlertResult(business_rule=business_rule, description=description))

    def remove_alert(self, business_rule: str) -> None:
        """Usuwa wszystkie alerty o danym business_rule z kolejki."""
        self._alerts = [a for a in self._alerts if a.business_rule != business_rule]

    def ok(self, instructions: dict = None) -> RulesResult:
        """
        Brak stopu — test kontynuuje.
        Użyj gdy:
          - brak alertów:                    return self.ok()
          - instrukcje dla kolejnego etapu:  return self.ok(instructions={...})
        """
        alerts, self._alerts = self._alerts, []
        return RulesResult(alerts=alerts, instructions=instructions or {})

    def stop(self, reason: str, instructions: dict = None) -> RulesResult:
        """
        Zatrzymaj test — dalsze etapy nie mają sensu.
        Użyj gdy brak danych/możliwości do kontynuowania:
          - pusty koszyk
          - brak wymaganej dostawy
          - brak wymaganej płatności
          - krytyczny błąd strony
        """
        alerts, self._alerts = self._alerts, []
        return RulesResult(alerts=alerts, should_stop=True, stop_reason=reason, instructions=instructions or {})
