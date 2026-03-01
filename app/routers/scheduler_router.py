from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.scheduled_job import ScheduledJob
from app.models.suite import Suite
from app.models.environment import Environment
from app.templates import templates
from app.scheduler import compute_next_run

router = APIRouter(tags=["scheduler"])


@router.get("/scheduler")
async def scheduler_list(request: Request, db: Session = Depends(get_db)):
    jobs = (
        db.query(ScheduledJob)
        .order_by(ScheduledJob.id)
        .all()
    )
    suites = db.query(Suite).filter(Suite.is_active == True).all()
    environments = db.query(Environment).filter(Environment.is_active == True).all()

    return templates.TemplateResponse("scheduler_list.html", {
        "request": request,
        "jobs": jobs,
        "suites": suites,
        "environments": environments,
    })


@router.post("/scheduler")
async def scheduler_create(
    suite_id: int = Form(...),
    environment_id: int = Form(...),
    workers: int = Form(...),
    cron: str = Form(...),
    db: Session = Depends(get_db),
):
    next_run = compute_next_run(cron)
    if next_run is None:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowe wyrażenie cron: '{cron}'")

    job = ScheduledJob(
        suite_id=suite_id,
        environment_id=environment_id,
        workers=workers,
        cron=cron,
        is_enabled=True,
        next_run_at=next_run,
    )
    db.add(job)
    db.commit()
    return RedirectResponse(url="/scheduler", status_code=303)


@router.post("/scheduler/{job_id}/toggle")
async def scheduler_toggle(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_enabled = not job.is_enabled

    # Po włączeniu — przelicz next_run_at
    if job.is_enabled:
        job.next_run_at = compute_next_run(job.cron)

    db.commit()
    return RedirectResponse(url="/scheduler", status_code=303)


@router.post("/scheduler/{job_id}/delete")
async def scheduler_delete(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return RedirectResponse(url="/scheduler", status_code=303)


@router.post("/scheduler/{job_id}/run-now")
async def scheduler_run_now(job_id: int, db: Session = Depends(get_db)):
    """Uruchamia job natychmiast — niezależnie od harmonogramu."""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.routers.execute import _start_suite
    from datetime import datetime, timezone

    try:
        suite_run_id = await _start_suite(
            suite_id=job.suite_id,
            environment_id=job.environment_id,
            workers_override=job.workers,
            headless=True,
            triggered_by="scheduler",
        )
        job.last_run_at = datetime.now(timezone.utc)
        job.last_suite_run_id = suite_run_id
        db.commit()
        return RedirectResponse(url=f"/suite-runs/{suite_run_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
