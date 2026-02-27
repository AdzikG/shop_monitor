from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Global — dane ze wszystkich etapów ───────────────────────────────────────

class GlobalRules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        alerts = []

        # Cena produktu na listingu vs cena w koszyku
        if run_data.listing and run_data.cart0:
            if run_data.listing.price and run_data.cart0.total_price:
                if abs(run_data.listing.price - run_data.cart0.total_price) > 0.01:
                    alerts.append(self.alert(
                        'GLOBAL_PRICE_CHANGED',
                        f'Cena zmieniła się: listing {run_data.listing.price} → koszyk {run_data.cart0.total_price}',
                    ))

        # Gwarancja widoczna w podsumowaniu
        if self.context.guarantee and run_data.cart4:
            # TODO: gdy znamy selektory
            pass

        return self.ok(alerts=alerts)