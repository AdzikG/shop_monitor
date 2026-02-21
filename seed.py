"""
Seed — wypelnia baze przykladowymi danymi.
Uruchom raz po 'alembic upgrade head'.

Uzycie:
    python seed.py
"""

from database import SessionLocal
from app.models.environment import Environment
from app.models.suite import Suite
from app.models.suite_environment import SuiteEnvironment
from app.models.scenario import Scenario
from app.models.suite_scenario import SuiteScenario


def seed():
    db = SessionLocal()
    try:
        # ── Srodowiska ────────────────────────────────────────────
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

        # ── Suite ─────────────────────────────────────────────────
        suite_bez_zamowien = Suite(
            name="Bez zamowien",
            description="Weryfikacja procesow koszykowych bez skladania zamowien",
            workers=2,
        )
        db.add(suite_bez_zamowien)
        db.flush()

        # ── Przypisanie Suite do Srodowisk ────────────────────────
        db.add(SuiteEnvironment(
            suite_id=suite_bez_zamowien.id,
            environment_id=pre.id,
            cron_expression="0 9,12,15 * * *",
            workers_override=2,
        ))
        db.add(SuiteEnvironment(
            suite_id=suite_bez_zamowien.id,
            environment_id=prod.id,
            cron_expression="0 9 * * *",
            workers_override=1,
        ))

        # ── Scenariusze ───────────────────────────────────────────
        s1 = Scenario(
            name="Elektronika - laptop",
            listing_urls=["https://www.amazon.pl/s?k=laptop"],
            delivery_name="Kurier",
            payment_name="Karta",
            postal_code="00-001",
            should_order=False,
        )
        s2 = Scenario(
            name="Ksiazki - Python",
            listing_urls=["https://www.amazon.pl/s?k=python+programming"],
            delivery_name="Paczkomat",
            payment_name="Przelew",
            postal_code="30-001",
            should_order=False,
        )
        db.add_all([s1, s2])
        db.flush()

        # ── Przypisanie Scenariuszy do Suite ──────────────────────
        db.add(SuiteScenario(suite_id=suite_bez_zamowien.id, scenario_id=s1.id, order=1))
        db.add(SuiteScenario(suite_id=suite_bez_zamowien.id, scenario_id=s2.id, order=2))

        db.commit()

        print("Seed zakończony. Dane w bazie:")
        print(f"  Srodowiska: PRE (id={pre.id}), PROD (id={prod.id})")
        print(f"  Suite: '{suite_bez_zamowien.name}' (id={suite_bez_zamowien.id})")
        print(f"  Scenariusze: {s1.name} (id={s1.id}), {s2.name} (id={s2.id})")
        print()
        print("Uruchom teraz:")
        print("  python main.py --suite 1 --environment 1")

    except Exception as e:
        db.rollback()
        print(f"Blad seeda: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
