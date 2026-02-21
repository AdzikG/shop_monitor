"""
Wypelnia domyslne typy alertow.
Uruchom po migracji: python seed_alert_types.py
"""

from database import SessionLocal
from app.models.alert_type import AlertType


def seed_alert_types():
    db = SessionLocal()
    
    try:
        # Sprawdz czy juz sa typy
        if db.query(AlertType).count() > 0:
            print("Typy alertow juz istnieja. Pomijam.")
            return
        
        # Domyslne typy
        types = [
            AlertType(
                name="Błąd",
                slug="bug",
                color="#ff0055",
                description="Rzeczywisty błąd wymagający naprawy",
                is_active=True
            ),
            AlertType(
                name="Do weryfikacji",
                slug="to_verify",
                color="#ffdd00",
                description="Wymaga weryfikacji czy to błąd",
                is_active=True
            ),
            AlertType(
                name="Do poprawy",
                slug="to_improve",
                color="#ff8800",
                description="Scenariusz działa ale wymaga poprawy",
                is_active=True
            ),
            AlertType(
                name="Wyłączony",
                slug="disabled",
                color="#666666",
                description="Alert tymczasowo wyłączony",
                is_active=True
            ),
        ]
        
        for t in types:
            db.add(t)
        
        db.commit()
        
        print(f"Utworzono {len(types)} typów alertów:")
        for t in types:
            print(f"  - {t.name} ({t.slug})")
        
    except Exception as e:
        db.rollback()
        print(f"Błąd: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_alert_types()
