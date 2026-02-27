from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart3 — adres ─────────────────────────────────────────────────────────────

class Cart3Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart3 = run_data.cart3
        alerts = []

        if self.context.postal_code and cart3.postal_code:
            if cart3.postal_code != self.context.postal_code:
                alerts.append(self.alert(
                    'CART3_POSTAL_MISMATCH',
                    f'Kod pocztowy: oczekiwano {self.context.postal_code}, jest {cart3.postal_code}',
                    alert_type='to_verify',
                ))

        return self.ok(alerts=alerts)

