from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart1 — transporty ────────────────────────────────────────────────────────

class Cart1Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart1 = run_data.cart1
        alerts = []

        # Oczekiwana dostawa niedostępna na liście
        if self.context.delivery_name and self.context.delivery_name not in cart1.available_options:
            return self.stop(
                alerts=[self.alert(
                    'CART1_DELIVERY_UNAVAILABLE',
                    f'Dostawa "{self.context.delivery_name}" niedostępna',
                    f'Dostępne: {", ".join(cart1.available_options)}',
                )],
                reason=f'Brak dostawy "{self.context.delivery_name}"',
            )

        # Dostawa była na liście ale nie udało się jej wybrać
        if self.context.delivery_name and not cart1.selected:
            return self.stop(
                alerts=[self.alert(
                    'CART1_DELIVERY_NOT_SELECTED',
                    f'Nie można wybrać dostawy "{self.context.delivery_name}"',
                )],
                reason='Nie można wybrać dostawy',
            )

        # Page widział pole kodu pocztowego ale nie miał czym wypełnić
        if cart1.postal_code_required and not cart1.postal_code_filled:
            return self.stop(
                alerts=[self.alert(
                    'CART1_POSTAL_CODE_MISSING',
                    'Dostawa wymaga kodu pocztowego — brak kodu w konfiguracji scenariusza',
                    alert_type='config',
                )],
                reason='Brak kodu pocztowego',
            )

        # Godzina graniczna niezgodna z oczekiwaną — alert ale kontynuujemy
        if self.context.delivery_cutoff and cart1.cutoff_time:
            if cart1.cutoff_time != self.context.delivery_cutoff:
                alerts.append(self.alert(
                    'CART1_CUTOFF_MISMATCH',
                    f'Godzina graniczna: oczekiwano {self.context.delivery_cutoff}, jest {cart1.cutoff_time}',
                    alert_type='to_verify',
                ))

        return self.ok(alerts=alerts)
