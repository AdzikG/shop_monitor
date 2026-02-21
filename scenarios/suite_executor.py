"""
Suite Executor — uruchamia cala suite i agreguje wyniki.
"""

import asyncio
import logging
import sys
import traceback
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.models.run import RunStatus
from app.models.alert_group import AlertGroup, AlertStatus
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

        # Skonfiguruj logger dla tego suite run
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
                        suite_run_id=suite_run.id,
                        suite_id=self.suite.id,
                        environment_id=self.environment.id,
                        base_url=self.environment.base_url,
                        db=db_session,
                        headless=self.headless
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
                    # Loguj krótko do structured log
                    logger.error(f"Blad w scenariuszu {scenario.name}: {e}")
                    
                    # Zapisz pełny traceback do raw log
                    self._write_raw_traceback(scenario.name, e)
                    
                    return {'scenario_id': scenario.id, 'status': 'failed', 'alerts': []}
                finally:
                    db_session.close()
        
        tasks = [run_with_limit(s) for s in self.scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Loguj exceptions które przeszły przez gather
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception w scenariuszu {self.scenarios[i].name}: {result}")
                self._write_raw_traceback(self.scenarios[i].name, result)

        self._finalize_suite_run(suite_run, results)
        
        # Usuń handler po zakończeniu
        if self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)
            self.log_handler.close()
        
        return suite_run

    def _write_raw_traceback(self, scenario_name: str, exception: Exception):
        """Zapisuje surowy traceback bezpośrednio do pliku."""
        if not self.log_file:
            return
        
        try:
            # Sformatuj traceback jako string
            tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
            tb_text = ''.join(tb_lines)
            
            # Zapisz bezpośrednio z prawdziwymi \n
            with open(self.log_file, 'a', encoding='utf-8', newline='') as f:
                f.write('=' * 80 + '\n')
                f.write(f'ERROR in scenario: {scenario_name}\n')
                f.write('=' * 80 + '\n')
                f.write(tb_text)
                f.write('=' * 80 + '\n')
                f.write('\n')
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write traceback: {e}")

    def _setup_logging(self):
        """Konfiguruje logger zeby zapisywal do pliku dla tego suite run."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        self.log_file = log_dir / f"suite_run_{self.suite_run_id}.log"
        
        # Dodaj file handler
        self.log_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.log_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
        self.log_handler.setFormatter(formatter)
        
        # Dodaj do root logger
        logging.getLogger().addHandler(self.log_handler)

    def _finalize_suite_run(self, suite_run: SuiteRun, results: list):
        """Agreguje wyniki scenariuszy i tworzy alert_groups."""
        
        success = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                continue
            if result['status'] == "success":
                success += 1
            else:
                failed += 1
        
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
                    group['alert_type'] = alert['alert_type']
                    group['title'] = alert['title']
                
                group['scenario_ids'].append(result['scenario_id'])
                group['count'] += 1
        
        total_alerts = 0
        for group_data in alert_groups_data.values():
            alert_group = AlertGroup(
                suite_run_id=suite_run.id,
                business_rule=group_data['business_rule'],
                alert_type=group_data['alert_type'],
                title=group_data['title'],
                occurrence_count=group_data['count'],
                scenario_ids=str(group_data['scenario_ids']),
                status=AlertStatus.OPEN,
            )
            self.db.add(alert_group)
            total_alerts += group_data['count']
        
        suite_run.success_scenarios = success
        suite_run.failed_scenarios = failed
        suite_run.total_alerts = total_alerts
        suite_run.finished_at = datetime.now(timezone.utc)
        
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