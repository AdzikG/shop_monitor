.PHONY: help reset clean test panel run seed

help:
	@echo "Shop Monitor — Komendy"
	@echo ""
	@echo "  make reset        - Usuń bazę i utwórz od nowa (z seedem)"
	@echo "  make clean        - Usuń tylko runy (zachowaj konfigurację)"
	@echo "  make seed         - Wypełnij dane startowe"
	@echo "  make panel        - Uruchom panel webowy"
	@echo "  make test         - Uruchom suite #1 na RC"
	@echo "  make run SUITE=1  - Uruchom konkretną suite"

reset:
	python reset_database.py --force

clean:
	python clean_runs.py --force

seed:
	python seed.py
	python seed_alert_types.py

panel:
	python run_panel.py

test:
	python main.py --suite 1 --environment 1

run:
	python main.py --suite $(SUITE) --environment 1
