from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart2 — płatności ─────────────────────────────────────────────────────────

class Cart2Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart2 = run_data.cart2

        if self.context.payment_name and self.context.payment_name not in cart2.available_options:
            return self.stop(
                alerts=[self.alert(
                    'CART2_PAYMENT_UNAVAILABLE',
                    f'Płatność "{self.context.payment_name}" niedostępna',
                    f'Dostępne: {", ".join(cart2.available_options)}',
                )],
                reason=f'Brak płatności "{self.context.payment_name}"',
            )

        if self.context.payment_name and not cart2.selected:
            return self.stop(
                alerts=[self.alert(
                    'CART2_PAYMENT_NOT_SELECTED',
                    f'Nie można wybrać płatności "{self.context.payment_name}"',
                )],
                reason='Nie można wybrać płatności',
            )

        return self.ok()


