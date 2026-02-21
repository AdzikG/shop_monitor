"""
Czysci baze z runow i alertow, zostawia scenariusze/suite/environments.

Uzycie:
    python clean_runs.py
"""

from database import SessionLocal
from app.models.suite_run import SuiteRun
from app.models.run import ScenarioRun
from app.models.alert import Alert
from app.models.alert_group import AlertGroup
from app.models.basket_snapshot import BasketSnapshot
from app.models.api_error import ApiError


def clean_runs():
    db = SessionLocal()
    
    print("Czyszczenie bazy...")
    print()
    
    try:
        # Zlicz przed usunieciem
        suite_runs_count = db.query(SuiteRun).count()
        scenario_runs_count = db.query(ScenarioRun).count()
        alerts_count = db.query(Alert).count()
        alert_groups_count = db.query(AlertGroup).count()
        snapshots_count = db.query(BasketSnapshot).count()
        api_errors_count = db.query(ApiError).count()
        
        print(f"Do usuniecia:")
        print(f"  Suite runs:       {suite_runs_count}")
        print(f"  Scenario runs:    {scenario_runs_count}")
        print(f"  Alerts:           {alerts_count}")
        print(f"  Alert groups:     {alert_groups_count}")
        print(f"  Basket snapshots: {snapshots_count}")
        print(f"  API errors:       {api_errors_count}")
        print()
        
        if suite_runs_count == 0 and scenario_runs_count == 0:
            print("Baza juz czysta!")
            return
        
        # Potwierdz
        confirm = input("Czy na pewno usunac? (tak/nie): ")
        if confirm.lower() != "tak":
            print("Anulowano.")
            return
        
        print()
        print("Usuwam...")
        
        # Usun w kolejnosci (od zaleznych do glownych)
        # 1. Basket snapshots i API errors (zaleza od scenario_runs)
        db.query(BasketSnapshot).delete()
        db.query(ApiError).delete()
        
        # 2. Alerts (zaleza od scenario_runs)
        db.query(Alert).delete()
        
        # 3. Alert groups (zaleza od suite_runs)
        db.query(AlertGroup).delete()
        
        # 4. Scenario runs (zaleza od suite_runs)
        db.query(ScenarioRun).delete()
        
        # 5. Suite runs (glowne)
        db.query(SuiteRun).delete()
        
        db.commit()
        
        print()
        print("Gotowe! Baza wyczyszczona.")
        print("Scenariusze, suite i environments zostaly zachowane.")
        
    except Exception as e:
        db.rollback()
        print(f"Blad: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clean_runs()