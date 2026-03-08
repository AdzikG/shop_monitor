from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart3 — adres ─────────────────────────────────────────────────────────────

class Cart3Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart3 = run_data.cart3

        if self.context.postal_code and cart3.postal_code:
            if cart3.postal_code != self.context.postal_code:
                self.add_alert(
                    'CART3_POSTAL_MISMATCH',
                    f'Kod pocztowy: oczekiwano {self.context.postal_code}, jest {cart3.postal_code}',
                )

        return self.ok()
