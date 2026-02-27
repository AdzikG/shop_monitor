from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart4 — podsumowanie ──────────────────────────────────────────────────────

class Cart4Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart4 = run_data.cart4
        alerts = []

        # Cena w podsumowaniu vs koszyk + dostawa
        if run_data.cart0 and cart4.total_price and run_data.cart0.total_price:
            delivery_price = run_data.cart1.price if run_data.cart1 else 0
            expected = run_data.cart0.total_price + (delivery_price or 0)
            if abs(cart4.total_price - expected) > 0.01:
                alerts.append(self.alert(
                    'CART4_PRICE_MISMATCH',
                    f'Cena w podsumowaniu ({cart4.total_price}) różni się od oczekiwanej ({expected:.2f})',
                ))

        # Weryfikacja dostawy w podsumowaniu vs wybrana w cart1
        if self.context.delivery_name and cart4.delivery_name:
            if self.context.delivery_name not in cart4.delivery_name:
                alerts.append(self.alert(
                    'CART4_DELIVERY_MISMATCH',
                    f'Dostawa w podsumowaniu "{cart4.delivery_name}" != "{self.context.delivery_name}"',
                ))

        # Weryfikacja płatności w podsumowaniu vs wybrana w cart2
        if self.context.payment_name and cart4.payment_name:
            if self.context.payment_name not in cart4.payment_name:
                alerts.append(self.alert(
                    'CART4_PAYMENT_MISMATCH',
                    f'Płatność w podsumowaniu "{cart4.payment_name}" != "{self.context.payment_name}"',
                ))

        return self.ok(alerts=alerts)
