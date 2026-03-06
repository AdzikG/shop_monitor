"""
Reset Database — usuwa bazę i tworzy od nowa ze strukturą i seedem.

UWAGA: Usuwa WSZYSTKIE dane!

Użycie:
    python reset_database.py              # interaktywne potwierdzenie
    python reset_database.py --force      # bez pytania
    python reset_database.py --keep-seed  # bez seed (tylko struktura)
    python reset_database.py --only-temp  # usuwa tylko pliki tymczasowe (logi, screeny)
"""

import sys
import os
import shutil
from pathlib import Path
import subprocess


def reset_database(force: bool = False, seed: bool = True, only_temp: bool = False):
    """
    Czyści pliki tymczasowe.
    Usuwa bazę i tworzy od nowa.
    """

    # Potwierdzenie
    if not force and not only_temp:
        print("⚠️  UWAGA: To usunie WSZYSTKIE dane z bazy oraz pliki tymczasowe!")
        confirm = input("Czy kontynuować? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Anulowano.")
            return
        only_temp, force = True, True

    if only_temp:
        print("\n🧹 Czyszczenie starych plików tymczasowych...")
        # Usuń logi, screenshoty i stare wyniki
        logs_dir = Path("logs/")
        if logs_dir.exists():
            deleted = 0
            for log_file in logs_dir.glob("*.log"):
                log_file.unlink()
                deleted += 1
            if deleted == 0:
                print("   Brak starych logów")
            else:
                print(f"   Usunięto {deleted} logów")

        screenshots_dir = Path("screenshots/")
        if screenshots_dir.exists():
            deleted = 0
            for screenshots_folder in screenshots_dir.iterdir():
                shutil.rmtree(screenshots_folder)
                deleted += 1
            if deleted == 0:
                print("   Brak starych screenshots")
            else:
                print(f"   Usunięto {deleted} folderów ze screenami")

        results_dir = Path("results/")
        if results_dir.exists():
            deleted = 0
            for results_file in results_dir.iterdir():
                if results_file.is_file():
                    results_file.unlink()
                    deleted += 1
                elif results_file.is_dir():
                    shutil.rmtree(results_file)
                    deleted += 1
            if deleted == 0:
                print("   Brak starych rezultatów")
            else:
                print(f"   Usunięto {deleted} folderów/plików z wynikami")
        
        if not force:
            return
    
    
    print("\n🗑️  Usuwanie starej bazy...")
    db_file = Path("shop_monitor.db")
    db_shm = Path("shop_monitor.db-shm")
    db_wal = Path("shop_monitor.db-wal")
    
    # Usuń pliki bazy
    for f in [db_file, db_shm, db_wal]:
        if f.exists():
            f.unlink()
            print(f"   Usunięto: {f}")
    
    # Usuń STARE MIGRACJE (ważne!)
    print("\n🧹 Czyszczenie starych migracji...")
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        deleted = 0
        for migration_file in versions_dir.glob("*.py"):
            if migration_file.name != "__init__.py":
                migration_file.unlink()
                deleted += 1
                print(f"   Usunięto: {migration_file.name}")
        if deleted == 0:
            print("   Brak starych migracji")

   
    print("\n🏗️  Generowanie nowej migracji...")
    # Wygeneruj nową migrację z aktualnych modeli
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "initial_schema"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Błąd podczas generowania migracji:")
        print(result.stderr)
        sys.exit(1)

    print("✅ Migracja wygenerowana")

    print("\n🏗️  Tworzenie nowej struktury bazy...")
    
    # Uruchom migracje
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Błąd podczas tworzenia struktury:")
        print(result.stderr)
        sys.exit(1)
    
    print("✅ Struktura utworzona")
    
    if seed:
        print("\n🌱 Wypełnianie danymi startowymi...")
        
        # Seed podstawowych danych
        result = subprocess.run(["python", "seed.py"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Błąd podczas seed.py:")
            print(result.stderr)
            sys.exit(1)
        print("✅ seed.py — OK")
        
        # Seed typów alertów
        result = subprocess.run(["python", "seed_alert_types.py"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Błąd podczas seed_alert_types.py:")
            print(result.stderr)
            sys.exit(1)
        print("✅ seed_alert_types.py — OK")
    
    print("\n✨ Baza zresetowana pomyślnie!")
    print("\nMożesz teraz:")
    print("  • python main.py --suite 1 --environment 1")
    print("  • python run_panel.py")


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    seed = "--keep-seed" not in sys.argv
    only_temp = "--only-temp" in sys.argv or force
    
    reset_database(force=force, seed=seed, only_temp=only_temp)
