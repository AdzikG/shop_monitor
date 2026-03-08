from scenarios.run_data import RunData
from scenarios.rules_result import RulesResult
from scenarios.rules.base_rules import BaseRules


# ── Listing ───────────────────────────────────────────────────────────────────

class ListingRules(BaseRules):
    def check(self, run_data: RunData) -> RulesResult:
        if not run_data.listing or not run_data.listing.available:
            self.add_alert('PRODUCT_UNAVAILABLE', 'Produkt niedostępny na listingu')
            return self.stop(reason='Produkt niedostępny')
        return self.ok()
