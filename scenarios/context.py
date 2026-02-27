from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class ScenarioContext:
    # Identyfikacja
    scenario_id: int
    scenario_name: str
    environment_url: str
    environment_name: str

    # Konfiguracja koszyka
    listing_urls: list[str]
    delivery_name: Optional[str] = None
    delivery_cutoff: Optional[str] = None
    payment_name: Optional[str] = None
    basket_type: Optional[str] = None
    postal_code: Optional[str] = None
    guarantee: bool = False
    is_order: bool = False
    services: list[str] = field(default_factory=list)

    # Flagi — {name: is_enabled}
    flags: dict[str, bool] = field(default_factory=dict)

    def flag(self, name: str, default: bool = False) -> bool:
        return self.flags.get(name, default)

    @property
    def is_mobile(self) -> bool:
        return self.flag('mobile')

    @property
    def is_desktop(self) -> bool:
        return not self.flag('mobile')

    @classmethod
    def from_db(cls, scenario, environment) -> "ScenarioContext":
        services = []
        if scenario.services:
            try:
                services = json.loads(scenario.services)
            except (ValueError, TypeError):
                pass

        flags = {sf.flag.name: sf.is_enabled for sf in scenario.flags}

        return cls(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            environment_url=environment.url,
            environment_name=environment.name,
            listing_urls=scenario.listing_urls or [],
            delivery_name=scenario.delivery_name,
            delivery_cutoff=scenario.delivery_cutoff,
            payment_name=scenario.payment_name,
            basket_type=scenario.basket_type,
            postal_code=scenario.postal_code,
            guarantee=scenario.guarantee or False,
            is_order=scenario.is_order or False,
            services=services,
            flags=flags,
        )
