from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from app.models.run import ScenarioRun
from app.models.alert import Alert
from app.models.basket_snapshot import BasketSnapshot
from app.templates import templates

router = APIRouter()


@router.get("/")
async def runs_list(request: Request, db: Session = Depends(get_db)):
    """Lista wszystkich uruchomień."""
    runs = (
        db.query(ScenarioRun)
        .order_by(desc(ScenarioRun.started_at))
        .limit(100)
        .all()
    )
    return templates.TemplateResponse("runs_list.html", {
        "request": request,
        "runs": runs,
    })


@router.get("/{run_id}")
async def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    """Szczegóły uruchomienia — alerty, snapshoty koszyka."""
    run = db.query(ScenarioRun).filter(ScenarioRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    alerts = db.query(Alert).filter(Alert.run_id == run_id).all()
    snapshots = db.query(BasketSnapshot).filter(BasketSnapshot.run_id == run_id).all()
    
    return templates.TemplateResponse("run_detail.html", {
        "request": request,
        "run": run,
        "alerts": alerts,
        "snapshots": snapshots,
    })
