"""
Clean Runs — usuwa wszystkie runy zachowując konfigurację.

Usuwa:
- suite_runs, scenario_runs, alerts, alert_groups
- basket_snapshots, api_errors
- logi z katalogu logs/

Zachowuje:
- suites, scenarios, environments, suite_scenarios, suite_environments
- alert_configs, alert_types

Użycie:
    python clean_runs.py              # interaktywne potwierdzenie
    python clean_runs.py --force      # bez pytania
    python clean_runs.py --keep-logs  # nie usuwaj logów
"""

import sys
from pathlib import Path
from database import SessionLocal
from app.models.basket_snapshot import BasketSnapshot
from app.models.api_error import ApiError
from app.models.alert import Alert
from app.models.alert_group import AlertGroup
from app.models.run import ScenarioRun
from app.models.suite_run import SuiteRun


def clean_runs(force: bool = False, keep_logs: bool = False):
    """Usuwa wszystkie runy zachowując konfigurację."""
    
    db = SessionLocal()
    
    # Potwierdzenie
    if not force:
        print("⚠️  UWAGA: To usunie wszystkie runy (dane testów) ale zachowa konfigurację!")
        confirm = input("Czy kontynuować? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Anulowano.")
            return
    
    try:
        print("\n🗑️  Usuwanie runów...")
        
        # Kolejność ważna — od zależnych do głównych
        counts = {}
        
        # 1. Zależności scenario_runs
        counts['basket_snapshots'] = db.query(BasketSnapshot).delete()
        counts['api_errors'] = db.query(ApiError).delete()
        counts['alerts'] = db.query(Alert).delete()
        
        # 2. Zależności suite_runs
        counts['alert_groups'] = db.query(AlertGroup).delete()
        
        # 3. Główne tabele
        counts['scenario_runs'] = db.query(ScenarioRun).delete()
        counts['suite_runs'] = db.query(SuiteRun).delete()
        
        db.commit()
        
        print("\n📊 Usunięte rekordy:")
        for table, count in counts.items():
            print(f"   {table}: {count}")
        
        # Usuń logi
        if not keep_logs:
            logs_dir = Path("logs")
            if logs_dir.exists():
                log_files = list(logs_dir.glob("*.log"))
                for log_file in log_files:
                    log_file.unlink()
                print(f"\n🗑️  Usunięto {len(log_files)} plików logów")
        
        print("\n✅ Runy wyczyszczone!")
        print("\nZachowano:")
        print("  • Suites, Scenarios, Environments")
        print("  • Alert Configs, Alert Types")
        print("  • Wszystkie konfiguracje")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Błąd: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    keep_logs = "--keep-logs" in sys.argv
    
    clean_runs(force=force, keep_logs=keep_logs)
