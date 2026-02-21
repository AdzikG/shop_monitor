# 1. Usuń bazę i historię migracji
rm shop_monitor.db
rm alembic/versions/*.py

# 2. Wygeneruj świeżą migrację od zera
alembic revision --autogenerate -m "initial schema with suite_runs"

# 3. Zastosuj
alembic upgrade head

# 4. Wypełnij danymi
python seed.py