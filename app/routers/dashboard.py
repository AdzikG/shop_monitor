from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.templates import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard — podsumowanie suite runs."""
    
    recent_runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .limit(20)
        .all()
    )
    
    total_runs = db.query(SuiteRun).count()
    failed_runs = db.query(SuiteRun).filter(
        SuiteRun.status.in_([SuiteRunStatus.FAILED, SuiteRunStatus.PARTIAL])
    ).count()
    total_alerts = sum(run.total_alerts for run in db.query(SuiteRun).all())
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recent_runs": recent_runs,
        "total_runs": total_runs,
        "failed_runs": failed_runs,
        "total_alerts": total_alerts,
    })


@router.get("/dashboard/runs-table")
async def dashboard_runs_table(request: Request, db: Session = Depends(get_db)):
    """Endpoint dla HTMX — zwraca tylko tabele do auto-refresh."""
    
    recent_runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .limit(20)
        .all()
    )
    
    return templates.TemplateResponse("dashboard_runs_table.html", {
        "request": request,
        "recent_runs": recent_runs,
    })
