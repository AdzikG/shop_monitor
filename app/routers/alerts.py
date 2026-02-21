from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from database import get_db
from app.models.alert_group import AlertGroup, AlertStatus
from app.templates import templates

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def alerts_list(
    request: Request,
    status: str = "active",  # active (open+in_progress) / closed / all
    search: str = "",
    db: Session = Depends(get_db)
):
    """
    Lista alertow z filtrowaniem i wyszukiwaniem.
    
    Parametry:
        status: active (open + in_progress) | closed | all
        search: szukaj po business_rule lub title
    """
    
    query = db.query(AlertGroup).order_by(desc(AlertGroup.first_seen_at))
    
    # Filtr statusu
    if status == "active":
        query = query.filter(AlertGroup.status.in_([AlertStatus.OPEN, AlertStatus.IN_PROGRESS]))
    elif status == "closed":
        query = query.filter(AlertGroup.status == AlertStatus.CLOSED)
    # "all" — bez filtra
    
    # Wyszukiwanie
    if search:
        query = query.filter(
            or_(
                AlertGroup.business_rule.ilike(f"%{search}%"),
                AlertGroup.title.ilike(f"%{search}%")
            )
        )
    
    alert_groups = query.limit(200).all()
    
    # Statystyki
    total_open = db.query(AlertGroup).filter(AlertGroup.status == AlertStatus.OPEN).count()
    total_in_progress = db.query(AlertGroup).filter(AlertGroup.status == AlertStatus.IN_PROGRESS).count()
    total_closed = db.query(AlertGroup).filter(AlertGroup.status == AlertStatus.CLOSED).count()
    
    return templates.TemplateResponse("alerts_list.html", {
        "request": request,
        "alert_groups": alert_groups,
        "current_status": status,
        "search_query": search,
        "total_open": total_open,
        "total_in_progress": total_in_progress,
        "total_closed": total_closed,
    })


@router.post("/alerts/{alert_group_id}/status")
async def update_alert_status(
    alert_group_id: int,
    new_status: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """Zmienia status alertu (open -> in_progress -> closed)."""
    
    alert_group = db.query(AlertGroup).filter(AlertGroup.id == alert_group_id).first()
    if not alert_group:
        return RedirectResponse(url="/alerts", status_code=303)
    
    alert_group.status = AlertStatus(new_status)
    
    if notes:
        alert_group.notes = notes
    
    if new_status == "closed":
        from datetime import datetime, timezone
        alert_group.closed_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return RedirectResponse(url="/alerts", status_code=303)
