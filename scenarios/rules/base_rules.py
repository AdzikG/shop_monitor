from scenarios.context import ScenarioContext
from scenarios.run_data import RunData
from scenarios.rules_result import AlertResult, RulesResult


class BaseRules:
    def __init__(self, context: ScenarioContext):
        self.context = context

    def check(self, run_data: RunData) -> RulesResult:
        raise NotImplementedError

    def alert(
        self,
        business_rule: str,
        description: str = "",
        alert_type: str = "bug",
    ) -> AlertResult:
        return AlertResult(
            business_rule=business_rule,
            description=description,
            alert_type=alert_type,
        )

    def ok(
        self,
        alerts: list[AlertResult] = None,
        instructions: dict = None,
    ) -> RulesResult:
        """
        Brak stopu — test kontynuuje.
        Użyj gdy:
          - brak alertów:                    return self.ok()
          - alerty ale test idzie dalej:     return self.ok(alerts=alerts)
          - instrukcje dla kolejnego etapu:  return self.ok(instructions={...})
          - oba:                             return self.ok(alerts=alerts, instructions={...})
        """
        return RulesResult(
            alerts=alerts or [],
            instructions=instructions or {},
        )

    def stop(
        self,
        alerts: list[AlertResult],
        reason: str,
        instructions: dict = None,
    ) -> RulesResult:
        """
        Zatrzymaj test — dalsze etapy nie mają sensu.
        Użyj gdy brak danych/możliwości do kontynuowania:
          - pusty koszyk
          - brak wymaganej dostawy
          - brak wymaganej płatności
          - krytyczny błąd strony
        """
        return RulesResult(
            alerts=alerts,
            should_stop=True,
            stop_reason=reason,
            instructions=instructions or {},
        )
