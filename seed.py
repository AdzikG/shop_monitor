"""
Seed — wypełnia bazę przykładowymi danymi.
Uruchom raz po reset_database.py --force.

Użycie:
    python seed.py
"""

from database import SessionLocal
from app.models.environment import Environment
from app.models.suite import Suite
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario
from app.models.dictionary import Dictionary
from app.models.flag_definition import FlagDefinition, ScenarioFlag
from app.models.alert_type import AlertType
from app.models.alert_config import AlertConfig
from app.models.scheduled_job import ScheduledJob


def seed():
    db = SessionLocal()
    try:

        # ── Słowniki ──────────────────────────────────────────────────────────
        dict_delivery = Dictionary(
            category="delivery",
            system_name="available_deliveries",
            display_name="Formy dostawy",
            description="Dostępne metody dostawy w sklepie",
            value="Kurier DPD, Kurier InPost, Paczkomat, Kurier DHL, Dostawa paletowa",
            value_type="list",
            order=1,
        )
        dict_payment = Dictionary(
            category="payment",
            system_name="available_payments",
            display_name="Formy płatności",
            description="Dostępne metody płatności",
            value="Karta kredytowa, BLIK, Przelew bankowy, PayPo, Raty",
            value_type="list",
            order=2,
        )
        dict_basket_type = Dictionary(
            category="basket_type",
            system_name="basket_types",
            display_name="Typy koszyka",
            description="Rodzaje koszyka / przesyłki",
            value="Paczka, Paleta, Koperta, Przesyłka ponadgabarytowa",
            value_type="list",
            order=3,
        )
        dict_services = Dictionary(
            category="service",
            system_name="available_services",
            display_name="Usługi dodatkowe",
            description="Dodatkowe usługi do zamówienia",
            value="Montaż, Ubezpieczenie, Gwarancja rozszerzona, Odbiór starego sprzętu, Pakowanie na prezent",
            value_type="list",
            order=4,
        )
        db.add_all([dict_delivery, dict_payment, dict_basket_type, dict_services])
        db.flush()

        # ── Definicje flag ────────────────────────────────────────────────────
        flag_skip_login = FlagDefinition(
            name="skip_login",
            display_name="Nie loguj",
            description="Pomiń logowanie — test jako gość",
        )
        flag_random_login = FlagDefinition(
            name="random_login",
            display_name="Losowe logowanie",
            description="Użyj losowego konta z puli testowej",
        )
        flag_cc_operator = FlagDefinition(
            name="cc_operator",
            display_name="Operator CC",
            description="Zaloguj jako operator Call Center",
        )
        flag_company_address = FlagDefinition(
            name="company_address",
            display_name="Adres firmowy",
            description="Wybierz adres na firmę (NIP, nazwa firmy)",
        )
        flag_different_delivery_address = FlagDefinition(
            name="different_delivery_address",
            display_name="Inny adres dostawy",
            description="Użyj adresu dostawy innego niż adres fakturowy",
        )
        db.add_all([
            flag_skip_login,
            flag_random_login,
            flag_cc_operator,
            flag_company_address,
            flag_different_delivery_address,
        ])
        db.flush()

        # ── Środowiska ────────────────────────────────────────────────────────
        pre = Environment(
            name="PRE",
            base_url="https://pre.twojsklep.pl",
            login="test@example.com",
            password="haslo123",
        )
        prod = Environment(
            name="PROD",
            base_url="https://www.twojsklep.pl",
        )
        db.add_all([pre, prod])
        db.flush()

        # ── Suite ─────────────────────────────────────────────────────────────
        suite_bez_zamowien = Suite(
            name="Bez zamówień",
            description="Weryfikacja procesów koszykowych bez składania zamówień",
            workers=2,
        )
        suite_manual = Suite(
            name="Manual Runs",
            description="Ręczne uruchomienia pojedynczych scenariuszy",
            workers=2,
        )
        db.add_all([suite_bez_zamowien, suite_manual])
        db.flush()

        # ── Scenariusze ───────────────────────────────────────────────────────
        s1 = Scenario(
            name="Elektronika - laptop",
            description="Test koszyka dla kategorii elektronika",
            listing_urls=["/s?k=laptop"],
            delivery_name="Kurier DPD",
            delivery_cutoff="15:00",
            payment_name="Karta kredytowa",
            basket_type="Paczka",
            postal_code="00-001",
            is_order=False,
            guarantee=False,
        )
        s2 = Scenario(
            name="Książki - Python",
            description="Test koszyka dla kategorii książki",
            listing_urls=["/s?k=python+programming"],
            delivery_name="Paczkomat",
            delivery_cutoff="20:00",
            payment_name="BLIK",
            basket_type="Koperta",
            postal_code="30-001",
            is_order=False,
            guarantee=False,
        )
        db.add_all([s1, s2])
        db.flush()

        # Flagi dla scenariusza 1
        db.add(ScenarioFlag(scenario_id=s1.id, flag_id=flag_random_login.id, is_enabled=True))
        db.add(ScenarioFlag(scenario_id=s1.id, flag_id=flag_company_address.id, is_enabled=False))

        # Flagi dla scenariusza 2
        db.add(ScenarioFlag(scenario_id=s2.id, flag_id=flag_skip_login.id, is_enabled=True))

        # ── Przypisanie Scenariuszy do Suite ──────────────────────────────────
        db.add(SuiteScenario(suite_id=suite_bez_zamowien.id, scenario_id=s1.id, order=1))
        db.add(SuiteScenario(suite_id=suite_bez_zamowien.id, scenario_id=s2.id, order=2))

        # ── Alert types ───────────────────────────────────────────────────────
        at_bug    = AlertType(name="Błąd",           slug="bug",       color="#ff4444", description="Błąd krytyczny")
        at_verify = AlertType(name="Do weryfikacji", slug="to_verify", color="#ffaa00", description="Wymaga sprawdzenia")
        at_config = AlertType(name="Konfiguracja",   slug="config",    color="#4488ff", description="Problem z konfiguracją scenariusza")
        db.add_all([at_bug, at_verify, at_config])
        db.flush()

        # ── Alert configs ─────────────────────────────────────────────────────
        alert_configs = [
            AlertConfig(business_rule="HOME_NOT_LOADED",             name="Strona główna nie załadowała się",                      alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="PRODUCT_UNAVAILABLE",         name="Produkt niedostępny na listingu",                       alert_type_id=at_verify.id, is_active=True),
            AlertConfig(business_rule="CART0_EMPTY",                 name="Koszyk pusty po dodaniu produktu",                      alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART0_NO_PRICE",              name="Brak ceny w koszyku",                                   alert_type_id=at_verify.id, is_active=True),
            AlertConfig(business_rule="CART1_DELIVERY_UNAVAILABLE",  name="Oczekiwana dostawa niedostępna",                        alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART1_DELIVERY_NOT_SELECTED", name="Nie można wybrać dostawy",                              alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART1_POSTAL_CODE_MISSING",   name="Brak kodu pocztowego w konfiguracji scenariusza",       alert_type_id=at_config.id, is_active=True),
            AlertConfig(business_rule="CART1_CUTOFF_MISMATCH",       name="Godzina graniczna niezgodna z oczekiwaną",              alert_type_id=at_verify.id, is_active=True),
            AlertConfig(business_rule="CART2_PAYMENT_UNAVAILABLE",   name="Oczekiwana płatność niedostępna",                      alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART2_PAYMENT_NOT_SELECTED",  name="Nie można wybrać płatności",                           alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART3_POSTAL_MISMATCH",       name="Kod pocztowy w adresie niezgodny z oczekiwanym",        alert_type_id=at_verify.id, is_active=True),
            AlertConfig(business_rule="CART4_PRICE_MISMATCH",        name="Cena w podsumowaniu różni się od oczekiwanej",          alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART4_DELIVERY_MISMATCH",     name="Dostawa w podsumowaniu niezgodna z wybraną",            alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="CART4_PAYMENT_MISMATCH",      name="Płatność w podsumowaniu niezgodna z wybraną",           alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="GLOBAL_PRICE_CHANGED",        name="Cena produktu zmieniła się między listingiem a koszem", alert_type_id=at_bug.id,    is_active=True),
            AlertConfig(business_rule="scenario.unexpected_error",   name="Nieoczekiwany błąd scenariusza",                       alert_type_id=at_bug.id,    is_active=True),
        ]
        db.add_all(alert_configs)

        db.commit()

        print("OK Seed zakończony. Dane w bazie:")
        print(f"  Środowiska: PRE (id={pre.id}), PROD (id={prod.id})")
        print(f"  Suite: '{suite_bez_zamowien.name}' (id={suite_bez_zamowien.id})")
        print(f"         '{suite_manual.name}' (id={suite_manual.id})")
        print(f"  Scenariusze: {s1.name} (id={s1.id}), {s2.name} (id={s2.id})")
        print(f"  Słowniki: {dict_delivery.display_name}, {dict_payment.display_name}, "
              f"{dict_basket_type.display_name}, {dict_services.display_name}")
        print(f"  Flagi: {flag_skip_login.name}, {flag_random_login.name}, "
              f"{flag_cc_operator.name}, {flag_company_address.name}, "
              f"{flag_different_delivery_address.name}")
        print(f"  Alert types: bug, to_verify, config")
        print(f"  Alert configs: {len(alert_configs)} reguł")

    except Exception as e:
        db.rollback()
        print(f"BLAD Błąd seeda: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
