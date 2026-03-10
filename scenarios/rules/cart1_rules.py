from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart1 — transporty ────────────────────────────────────────────────────────

class Cart1Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart1 = run_data.cart1

        # Oczekiwana dostawa niedostępna na liście
        if self.scenario_context.delivery_name and self.scenario_context.delivery_name not in cart1.available_options:
            self.add_alert(
                'CART1_DELIVERY_UNAVAILABLE',
                f'Dostawa "{self.scenario_context.delivery_name}" niedostępna. Dostępne: {", ".join(cart1.available_options)}',
            )
            return self.stop(reason=f'Brak dostawy "{self.scenario_context.delivery_name}"')

        # Dostawa była na liście ale nie udało się jej wybrać
        if self.scenario_context.delivery_name and not cart1.selected:
            self.add_alert(
                'CART1_DELIVERY_NOT_SELECTED',
                f'Nie można wybrać dostawy "{self.scenario_context.delivery_name}"',
            )
            return self.stop(reason='Nie można wybrać dostawy')

        # Page widział pole kodu pocztowego ale nie miał czym wypełnić
        if cart1.postal_code_required and not cart1.postal_code_filled:
            self.add_alert('CART1_POSTAL_CODE_MISSING', 'Dostawa wymaga kodu pocztowego — brak kodu w konfiguracji scenariusza')
            return self.stop(reason='Brak kodu pocztowego')

        # Godzina graniczna niezgodna z oczekiwaną — alert ale kontynuujemy
        if self.scenario_context.delivery_cutoff and cart1.cutoff_time:
            if cart1.cutoff_time != self.scenario_context.delivery_cutoff:
                self.add_alert(
                    'CART1_CUTOFF_MISMATCH',
                    f'Godzina graniczna: oczekiwano {self.scenario_context.delivery_cutoff}, jest {cart1.cutoff_time}',
                )

        return self.ok()
