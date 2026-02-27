from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Cart0 ─────────────────────────────────────────────────────────────────────

class Cart0Rules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        cart0 = run_data.cart0
        alerts = []
        instructions = {}

        if not cart0 or cart0.item_count == 0:
            return self.stop(
                alerts=[self.alert('CART0_EMPTY', 'Koszyk pusty po dodaniu produktu')],
                reason='Pusty koszyk',
            )

        if cart0.total_price is None:
            alerts.append(self.alert('CART0_NO_PRICE', 'Brak ceny w koszyku', alert_type='to_verify'))

        # Instrukcje dla kolejnych etapów — logika biznesowa decyduje co przekazać
        if self.context.delivery_name in ('Kurier', 'Kurier jutro', 'Kurier 48h'):
            instructions['requires_postal_code'] = True

        if self.context.flag('company_address'):
            instructions['fill_company_fields'] = True

        return self.ok(alerts=alerts, instructions=instructions)