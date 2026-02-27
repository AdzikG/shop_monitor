from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HomeData:
    loaded: bool = False


@dataclass
class ProductData:
    name: Optional[str] = None
    price: Optional[float] = None
    url: Optional[str] = None
    available: bool = True


@dataclass
class Cart0Data:
    total_price: Optional[float] = None
    item_count: int = 0
    products: list[ProductData] = field(default_factory=list)


@dataclass
class Cart1Data:
    available_options: list[str] = field(default_factory=list)
    selected: Optional[str] = None
    estimated_date: Optional[str] = None
    cutoff_time: Optional[str] = None
    price: Optional[float] = None
    # Fakty zebrane przez page — oceniane przez rules
    postal_code_required: bool = False   # pole kodu pocztowego było widoczne
    postal_code_filled: bool = False     # udało się wpisać kod


@dataclass
class Cart2Data:
    available_options: list[str] = field(default_factory=list)
    selected: Optional[str] = None
    price: Optional[float] = None


@dataclass
class Cart3Data:
    postal_code: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    is_company: bool = False


@dataclass
class Cart4Data:
    total_price: Optional[float] = None
    delivery_name: Optional[str] = None
    delivery_price: Optional[float] = None
    payment_name: Optional[str] = None
    order_number: Optional[str] = None


@dataclass
class RunData:
    home:    Optional[HomeData]    = None
    listing: Optional[ProductData] = None
    cart0:   Optional[Cart0Data]   = None
    cart1:   Optional[Cart1Data]   = None
    cart2:   Optional[Cart2Data]   = None
    cart3:   Optional[Cart3Data]   = None
    cart4:   Optional[Cart4Data]   = None
