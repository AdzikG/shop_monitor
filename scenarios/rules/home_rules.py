from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Home ──────────────────────────────────────────────────────────────────────

class HomeRules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        if not run_data.home or not run_data.home.loaded:
            return self.stop(
                alerts=[self.alert('HOME_NOT_LOADED', 'Strona główna nie załadowała się')],
                reason='Strona główna niedostępna',
            )
        return self.ok()