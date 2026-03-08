from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AlertResult:
    business_rule: str
    description: str = ""


@dataclass
class RulesResult:
    alerts: list[AlertResult] = field(default_factory=list)
    should_stop: bool = False
    stop_reason: str = ""
    instructions: dict = field(default_factory=dict)
    # Przykłady instrukcji przekazywanych do kolejnych pages:
    # {'requires_postal_code': True}
    # {'skip_payment_step': True}
    # {'fill_company_fields': True}
