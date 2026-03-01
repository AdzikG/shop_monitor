"""
Scheduler — uruchamia zaplanowane joby według cron.
Tick odpala się co minutę i sprawdza które joby są do uruchomienia.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from database import SessionLocal
from app.models.scheduled_job import ScheduledJob
from core import runner_registry

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start():
    scheduler.add_job(tick, "interval", minutes=1, id="scheduler_tick", replace_existing=True)
    scheduler.start()
    logger.info("[Scheduler] Uruchomiony — tick co minutę")


def stop():
    scheduler.shutdown(wait=False)
    logger.info("[Scheduler] Zatrzymany")


async def tick():
    """Sprawdza które joby są do uruchomienia i odpala je."""
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        jobs = db.query(ScheduledJob).filter(
            ScheduledJob.is_enabled == True,
            ScheduledJob.next_run_at <= now,
        ).all()

        for job in jobs:
            logger.info(f"[Scheduler] Uruchamiam job #{job.id} — {job.suite.name} @ {job.environment.name}")
            try:
                # Import tutaj żeby uniknąć circular import
                from app.routers.execute import _start_suite
                suite_run_id = await _start_suite(
                    suite_id=job.suite_id,
                    environment_id=job.environment_id,
                    workers_override=job.workers,
                    headless=True,
                    triggered_by="scheduler",
                )
                job.last_run_at = now
                job.last_suite_run_id = suite_run_id
                logger.info(f"[Scheduler] Job #{job.id} uruchomiony jako suite_run #{suite_run_id}")
            except Exception as e:
                logger.error(f"[Scheduler] Błąd uruchamiania job #{job.id}: {e}")

            # Zawsze aktualizuj next_run_at — nawet jeśli był błąd
            job.next_run_at = _next_run(job.cron)

        if jobs:
            db.commit()

    except Exception as e:
        logger.error(f"[Scheduler] Błąd tick: {e}")
    finally:
        db.close()


def _next_run(cron: str) -> datetime:
    """Oblicza następny czas uruchomienia dla wyrażenia cron."""
    now = datetime.now(timezone.utc)
    cron_iter = croniter(cron, now)
    return cron_iter.get_next(datetime).replace(tzinfo=timezone.utc)


def compute_next_run(cron: str) -> datetime | None:
    """Publiczne API — waliduje cron i zwraca następny run. None jeśli błąd."""
    try:
        return _next_run(cron)
    except Exception:
        return None
