"""
Suite Executor — uruchamia cala suite i agreguje wyniki.
"""

import asyncio
import logging
import traceback
import json
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.models.alert_group import (
    AlertGroup, AlertStatus, ResolutionType,
    AWAITING_STATUSES, REOPEN_ON_RETURN, RESOLUTION_TO_STATUS
)
from app.models.alert import Alert
from scenarios.scenario_executor import ScenarioExecutor

logger = logging.getLogger(__name__)


class SuiteExecutor:
    """Orchestrator suite — tworzy suite_run, uruchamia scenariusze, agreguje alerty."""

    def __init__(self, suite, environment, scenarios, workers: int, headless: bool, db: Session):
        self.suite = suite
        self.environment = environment
        self.scenarios = scenarios
        self.workers = workers
        self.headless = headless
        self.db = db
        self.suite_run_id = None
        self.log_handler = None
        self.log_file = None

    async def run(self) -> SuiteRun:
        """Uruchamia cala suite i zwraca suite_run z wynikami."""

        suite_run = SuiteRun(
            suite_id=self.suite.id,
            environment_id=self.environment.id,
            status=SuiteRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            total_scenarios=len(self.scenarios),
        )
        self.db.add(suite_run)
        self.db.commit()
        self.db.refresh(suite_run)

        self.suite_run_id = suite_run.id
        self._setup_logging()

        logger.info(f"\n{'='*60}")
        logger.info(f"[SUITE RUN #{suite_run.id}] {self.suite.name} @ {self.environment.name}")
        logger.info(f"Scenariusze: {len(self.scenarios)} | Workers: {self.workers}")
        logger.info(f"{'='*60}\n")

        semaphore = asyncio.Semaphore(self.workers)

        async def run_with_limit(scenario):
            async with semaphore:
                db_session = Session(bind=self.db.bind)
                try:
                    executor = ScenarioExecutor(
                        scenario_db=scenario,
                        environment_db=self.environment,
                        suite_run_id=suite_run.id,
                        suite_id=self.suite.id,
                        db=db_session,
                        headless=self.headless,
                    )
                    run = await executor.run()

                    result = {
                        'scenario_id': run.scenario_id,
                        'status': run.status.value,
                        'alerts': []
                    }

                    for alert in run.alerts:
                        if alert.is_counted:
                            result['alerts'].append({
                                'business_rule': alert.business_rule,
                                'alert_type': alert.alert_type,
                                'title': alert.title,
                            })

                    return result

                except Exception as e:
                    logger.error(f"Blad w scenariuszu {scenario.name}: {e}")
                    self._write_raw_traceback(scenario.name, e)
                    return {'scenario_id': scenario.id, 'status': 'failed', 'alerts': []}
                finally:
                    db_session.close()

        tasks = [run_with_limit(s) for s in self.scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception w scenariuszu {self.scenarios[i].name}: {result}")
                self._write_raw_traceback(self.scenarios[i].name, result)

        self._finalize_suite_run(suite_run, results)

        if self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)
            self.log_handler.close()

        return suite_run

    def _write_raw_traceback(self, scenario_name: str, exception: Exception):
        if not self.log_file:
            return
        try:
            tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write('=' * 80 + '\n')
                f.write(f'ERROR in scenario: {scenario_name}\n')
                f.write('=' * 80 + '\n')
                f.write(''.join(tb_lines))
                f.write('=' * 80 + '\n\n')
        except Exception as e:
            logger.error(f"Failed to write traceback: {e}")

    @staticmethod
    def _parse_history(value) -> list:
        """Parsuje suite_run_history — obsługuje listę, string i podwójnie zakodowany JSON."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def _setup_logging(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / f"suite_run_{self.suite_run_id}.log"
        self.log_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.log_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)

    # ── Główna logika finalizacji ─────────────────────────────────────────────

    def _finalize_suite_run(self, suite_run: SuiteRun, results: list):
        """Agreguje wyniki scenariuszy i tworzy/aktualizuje alert_groups."""

        success = sum(1 for r in results if not isinstance(r, Exception) and r['status'] == 'success')
        failed  = sum(1 for r in results if isinstance(r, Exception) or r['status'] != 'success')

        # Zbierz alerty z tego runu pogrupowane po business_rule
        alert_groups_data = defaultdict(lambda: {
            'business_rule': '',
            'alert_type': '',
            'title': '',
            'scenario_ids': [],
            'count': 0
        })

        for result in results:
            if isinstance(result, Exception):
                continue
            for alert in result['alerts']:
                key = alert['business_rule']
                group = alert_groups_data[key]
                if not group['business_rule']:
                    group['business_rule'] = alert['business_rule']
                    group['alert_type']    = alert['alert_type']
                    group['title']         = alert['title']
                group['scenario_ids'].append(result['scenario_id'])
                group['count'] += 1

        # Zbiór business_rules które wystąpiły w tym runie
        active_rules = set(alert_groups_data.keys())

        # ── Krok 1: obsłuż alerty które WYSTĄPIŁY w tym runie ────────────────
        total_alerts = 0

        for group_data in alert_groups_data.values():
            total_alerts += group_data['count']
            self._handle_alert_occurred(suite_run, group_data)

        # ── Krok 2: obsłuż alerty które NIE wystąpiły (clean_runs_count++) ───
        self._handle_alerts_not_occurred(suite_run, active_rules)

        # ── Finalizacja suite_run ─────────────────────────────────────────────
        suite_run.success_scenarios = success
        suite_run.failed_scenarios  = failed
        suite_run.total_alerts      = total_alerts
        suite_run.finished_at       = datetime.now(timezone.utc)

        if failed == 0:
            suite_run.status = SuiteRunStatus.SUCCESS
        elif success == 0:
            suite_run.status = SuiteRunStatus.FAILED
        else:
            suite_run.status = SuiteRunStatus.PARTIAL

        self.db.commit()

        logger.info(f"\n{'='*60}")
        logger.info(f"[SUITE RUN #{suite_run.id}] COMPLETED")
        logger.info(f"Status: {suite_run.status.value.upper()}")
        logger.info(f"Success: {success} | Failed: {failed}")
        logger.info(f"Alerts: {total_alerts} ({len(alert_groups_data)} unique rules)")
        logger.info(f"Duration: {suite_run.duration_seconds}s")
        logger.info(f"{'='*60}\n")

    def _handle_alert_occurred(self, suite_run: SuiteRun, group_data: dict):
        """Obsługuje pojedynczy alert który wystąpił w tym runie."""

        scenario_ids_sorted = sorted(group_data['scenario_ids'])
        scenario_ids_json   = json.dumps(scenario_ids_sorted)

        # Szukaj kandydatów — wszystkie statusy poza CLOSED
        # (CLOSED duplikaty obsługujemy osobno poniżej)
        candidates = (
            self.db.query(AlertGroup)
            .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
            .filter(
                AlertGroup.business_rule == group_data['business_rule'],
                AlertGroup.status.in_([
                    AlertStatus.OPEN,
                    AlertStatus.IN_PROGRESS,
                    AlertStatus.AWAITING_FIX,
                    AlertStatus.AWAITING_TEST_UPDATE,
                ]),
                SuiteRun.environment_id == suite_run.environment_id
            )
            .all()
        )

        existing = self._find_matching_candidate(candidates, scenario_ids_sorted)

        if existing:
            self._update_existing_alert(existing, suite_run, scenario_ids_sorted, group_data)
            return

        # Brak aktywnego — sprawdź czy jest CLOSED DUPLICATE z aktywnym parentem
        closed_duplicate = self._find_closed_duplicate(
            group_data['business_rule'], suite_run.environment_id, scenario_ids_sorted
        )

        if closed_duplicate:
            # Parent nadal w toku — zostaje CLOSED, cichy repeat
            self._update_duplicate_alert(closed_duplicate, suite_run)
            return

        # Sprawdź czy jest CLOSED (NAB / CANT_REPRODUCE) który wraca
        closed_candidate = self._find_closed_candidate(
            group_data['business_rule'], suite_run.environment_id, scenario_ids_sorted
        )

        if closed_candidate and closed_candidate.resolution_type in (
            ResolutionType.NAB, ResolutionType.CANT_REPRODUCE
        ):
            # Reopen — wraca mimo że uznany za nieistotny
            self._reopen_alert(closed_candidate, suite_run, scenario_ids_sorted, group_data)
            return

        # Nowy AlertGroup
        self._create_new_alert(suite_run, group_data, scenario_ids_sorted, scenario_ids_json)

    def _handle_alerts_not_occurred(self, suite_run: SuiteRun, active_rules: set):
        """
        Dla alertów które NIE wystąpiły w tym runie — inkrementuje clean_runs_count.
        Nie zamyka automatycznie — kontrola po stronie użytkownika.
        """

        # Pobierz wszystkie aktywne alerty dla tego environment
        active_alerts = (
            self.db.query(AlertGroup)
            .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
            .filter(
                AlertGroup.status.in_([
                    AlertStatus.OPEN,
                    AlertStatus.IN_PROGRESS,
                    AlertStatus.AWAITING_FIX,
                    AlertStatus.AWAITING_TEST_UPDATE,
                ]),
                SuiteRun.environment_id == suite_run.environment_id
            )
            .all()
        )

        for alert in active_alerts:
            if alert.business_rule not in active_rules:
                alert.clean_runs_count += 1
                logger.info(
                    f"Alert {alert.business_rule} nie wystąpił "
                    f"(clean runs: {alert.clean_runs_count})"
                )

    # ── Helpers deduplikacji ──────────────────────────────────────────────────

    def _find_matching_candidate(self, candidates: list, scenario_ids_sorted: list):
        """Znajduje pierwszego kandydata którego scenario_ids pokrywają się (subset/superset)."""
        new_ids = set(scenario_ids_sorted)
        for candidate in candidates:
            try:
                existing_ids = set(json.loads(candidate.scenario_ids))
                if new_ids.issubset(existing_ids) or existing_ids.issubset(new_ids):
                    return candidate
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _find_closed_duplicate(self, business_rule: str, environment_id: int, scenario_ids_sorted: list):
        """
        Szuka CLOSED DUPLICATE którego parent jest nadal w AWAITING_FIX/AWAITING_TEST_UPDATE.
        """
        closed_candidates = (
            self.db.query(AlertGroup)
            .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
            .filter(
                AlertGroup.business_rule == business_rule,
                AlertGroup.status == AlertStatus.CLOSED,
                AlertGroup.resolution_type == ResolutionType.DUPLICATE,
                AlertGroup.duplicate_of_id.isnot(None),
                SuiteRun.environment_id == environment_id
            )
            .all()
        )

        new_ids = set(scenario_ids_sorted)
        for candidate in closed_candidates:
            try:
                existing_ids = set(json.loads(candidate.scenario_ids))
                if not (new_ids.issubset(existing_ids) or existing_ids.issubset(new_ids)):
                    continue
            except (json.JSONDecodeError, TypeError):
                continue

            # Sprawdź status parenta
            parent = self.db.query(AlertGroup).get(candidate.duplicate_of_id)
            if parent and parent.status in AWAITING_STATUSES:
                return candidate

        return None

    def _find_closed_candidate(self, business_rule: str, environment_id: int, scenario_ids_sorted: list):
        """Szuka CLOSED alertu (NAB/CANT_REPRODUCE) który wraca."""
        closed_candidates = (
            self.db.query(AlertGroup)
            .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
            .filter(
                AlertGroup.business_rule == business_rule,
                AlertGroup.status == AlertStatus.CLOSED,
                AlertGroup.resolution_type.in_([
                    ResolutionType.NAB, ResolutionType.CANT_REPRODUCE
                ]),
                SuiteRun.environment_id == environment_id
            )
            .order_by(AlertGroup.last_seen_at.desc())
            .first()
        )
        return closed_candidates

    # ── Akcje na AlertGroup ───────────────────────────────────────────────────

    def _update_existing_alert(self, existing: AlertGroup, suite_run: SuiteRun,
                                scenario_ids_sorted: list, group_data: dict):
        """Aktualizuje istniejący alert (OPEN/IN_PROGRESS/AWAITING_*)."""
        try:
            old_ids = set(json.loads(existing.scenario_ids))
        except (json.JSONDecodeError, TypeError):
            old_ids = set()

        merged_ids = sorted(old_ids | set(scenario_ids_sorted))
        existing.scenario_ids     = json.dumps(merged_ids)
        existing.repeat_count     += 1
        existing.clean_runs_count = 0
        existing.last_seen_at     = datetime.now(timezone.utc)
        existing.last_suite_run_id = suite_run.id
        existing.occurrence_count = group_data['count']

        # Aktualizuj historię
        try:
            history = self._parse_history(existing.suite_run_history)
        except (json.JSONDecodeError, TypeError):
            history = []
        history.append(suite_run.id)
        existing.suite_run_history = json.dumps(history)

        logger.info(
            f"Alert {existing.business_rule} powtórzył się "
            f"(status: {existing.status.value}, repeat: {existing.repeat_count}x)"
        )

    def _update_duplicate_alert(self, duplicate: AlertGroup, suite_run: SuiteRun):
        """Aktualizuje CLOSED DUPLICATE — cichy repeat, parent nadal w toku."""
        duplicate.repeat_count     += 1
        duplicate.clean_runs_count = 0
        duplicate.last_seen_at     = datetime.now(timezone.utc)
        duplicate.last_suite_run_id = suite_run.id

        try:
            history = self._parse_history(duplicate.suite_run_history)
        except (json.JSONDecodeError, TypeError):
            history = []
        history.append(suite_run.id)
        duplicate.suite_run_history = json.dumps(history)

        parent_id = duplicate.duplicate_of_id
        logger.info(
            f"Alert {duplicate.business_rule} — duplikat #{parent_id} nadal w toku, "
            f"cichy repeat (repeat: {duplicate.repeat_count}x)"
        )

    def _reopen_alert(self, alert: AlertGroup, suite_run: SuiteRun,
                      scenario_ids_sorted: list, group_data: dict):
        """Reopen CLOSED alertu (NAB/CANT_REPRODUCE) który wraca."""
        prev_resolution = alert.resolution_type

        try:
            old_ids = set(json.loads(alert.scenario_ids))
        except (json.JSONDecodeError, TypeError):
            old_ids = set()

        merged_ids = sorted(old_ids | set(scenario_ids_sorted))
        alert.scenario_ids      = json.dumps(merged_ids)
        alert.status            = AlertStatus.OPEN
        alert.repeat_count      += 1
        alert.clean_runs_count  = 0
        alert.last_seen_at      = datetime.now(timezone.utc)
        alert.last_suite_run_id = suite_run.id
        alert.occurrence_count  = group_data['count']
        # Zachowaj resolution_type jako kontekst — widoczne jako oznaczenie na liście
        # NIE czyścimy resolution_type żeby widok mógł pokazać "poprzednio: NAB"

        try:
            history = self._parse_history(alert.suite_run_history)
        except (json.JSONDecodeError, TypeError):
            history = []
        history.append(suite_run.id)
        alert.suite_run_history = json.dumps(history)

        logger.info(
            f"Alert {alert.business_rule} reopen — "
            f"poprzednio {prev_resolution}, wrócił po zamknięciu "
            f"(repeat: {alert.repeat_count}x)"
        )

    def _create_new_alert(self, suite_run: SuiteRun, group_data: dict,
                          scenario_ids_sorted: list, scenario_ids_json: str):
        """Tworzy nowy AlertGroup."""
        alert_group = AlertGroup(
            last_suite_run_id  = suite_run.id,
            suite_run_history  = json.dumps([suite_run.id]),
            business_rule      = group_data['business_rule'],
            alert_type         = group_data['alert_type'],
            title              = group_data['title'],
            occurrence_count   = group_data['count'],
            scenario_ids       = scenario_ids_json,
            repeat_count       = 1,
            clean_runs_count   = 0,
            status             = AlertStatus.OPEN,
            first_seen_at      = datetime.now(timezone.utc),
            last_seen_at       = datetime.now(timezone.utc),
        )
        self.db.add(alert_group)
        logger.info(f"Nowy alert: {alert_group.business_rule}")