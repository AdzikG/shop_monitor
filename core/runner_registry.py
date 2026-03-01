"""
RunnerRegistry — globalny rejestr uruchomionych suite.
Odpowiedzialności:
  1. Śledzi aktywne suite_run_id → Task
  2. Limituje liczbę równoległych suite (MAX_CONCURRENT_SUITES)
  3. Umożliwia anulowanie konkretnego runu
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

# Maksymalna liczba równolegle uruchomionych suite
MAX_CONCURRENT_SUITES = 3

# Globalny rejestr: suite_run_id → asyncio.Task
_running: dict[int, asyncio.Task] = {}

# Semaphore limitujący liczbę równoległych suite
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUITES)


def get_running() -> dict[int, asyncio.Task]:
    """Zwraca słownik aktywnych suite_run_id → Task."""
    return dict(_running)


def is_running(suite_run_id: int) -> bool:
    return suite_run_id in _running


def count_running() -> int:
    return len(_running)


def cancel(suite_run_id: int) -> bool:
    """
    Anuluje task dla podanego suite_run_id.
    Zwraca True jeśli task istniał i został anulowany.
    """
    task = _running.get(suite_run_id)
    if not task:
        return False
    task.cancel()
    logger.info(f"[RunnerRegistry] Anulowano suite_run #{suite_run_id}")
    return True


async def run_suite(suite_run_id: int, coro) -> None:
    """
    Uruchamia coroutine suite pod kontrolą semaphore i registry.
    Używaj zamiast bezpośredniego asyncio.create_task().

    Przykład:
        await run_suite(suite_run.id, run_suite_background(...))
    """
    if len(_running) >= MAX_CONCURRENT_SUITES:
        logger.warning(
            f"[RunnerRegistry] Limit {MAX_CONCURRENT_SUITES} równoległych suite osiągnięty — "
            f"suite_run #{suite_run_id} odrzucony"
        )
        raise RuntimeError(
            f"Osiągnięto limit {MAX_CONCURRENT_SUITES} równoległych suite. "
            f"Poczekaj na zakończenie bieżących."
        )

    async def _wrapper():
        async with _semaphore:
            try:
                await coro
            except asyncio.CancelledError:
                logger.info(f"[RunnerRegistry] suite_run #{suite_run_id} anulowany")
            except Exception as e:
                logger.exception(f"[RunnerRegistry] suite_run #{suite_run_id} błąd: {e}")
            finally:
                _running.pop(suite_run_id, None)
                logger.info(f"[RunnerRegistry] suite_run #{suite_run_id} zakończony — aktywnych: {len(_running)}")

    task = asyncio.create_task(_wrapper())
    _running[suite_run_id] = task
    logger.info(f"[RunnerRegistry] Zarejestrowano suite_run #{suite_run_id} — aktywnych: {len(_running)}")
