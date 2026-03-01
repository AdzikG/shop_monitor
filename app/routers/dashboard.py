from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta, timezone

from database import get_db
from app.models.suite_run import SuiteRun, SuiteRunStatus
from app.models.alert_group import AlertGroup, AlertStatus
from app.models.run import ScenarioRun, RunStatus
from app.templates import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # ── Liczniki alertów ──────────────────────────────────────────────────────
    active_alerts = db.query(AlertGroup).filter(
        AlertGroup.status.in_([AlertStatus.OPEN, AlertStatus.IN_PROGRESS])
    ).count()

    backlog_alerts = db.query(AlertGroup).filter(
        AlertGroup.status.in_([AlertStatus.AWAITING_FIX, AlertStatus.AWAITING_TEST_UPDATE])
    ).count()

    new_today = db.query(AlertGroup).filter(
        AlertGroup.first_seen_at >= today
    ).count()

    # ── Liczniki runów 24h ────────────────────────────────────────────────────
    scenarios_24h = db.query(ScenarioRun).filter(
        ScenarioRun.started_at >= today,
        ScenarioRun.status != RunStatus.CANCELLED
    ).count()

    failed_24h = db.query(ScenarioRun).filter(
        ScenarioRun.started_at >= today,
        ScenarioRun.status == "failed"
    ).count()

    # ── Trend tygodniowy ──────────────────────────────────────────────────────
    alerts_this_week = db.query(AlertGroup).filter(
        AlertGroup.first_seen_at >= week_ago
    ).count()

    alerts_last_week = db.query(AlertGroup).filter(
        AlertGroup.first_seen_at >= two_weeks_ago,
        AlertGroup.first_seen_at < week_ago
    ).count()

    if alerts_last_week > 0:
        trend_pct = round((alerts_this_week - alerts_last_week) / alerts_last_week * 100)
    elif alerts_this_week > 0:
        trend_pct = 100
    else:
        trend_pct = 0

    trend_up = trend_pct > 0

    # ── Top błędów ────────────────────────────────────────────────────────────
    from app.models.environment import Environment
    from sqlalchemy import and_

    prod_env = db.query(Environment).filter_by(name="PROD").first()

    top_alerts_raw = (
        db.query(AlertGroup)
        .join(SuiteRun, AlertGroup.last_suite_run_id == SuiteRun.id)
        .filter(
            AlertGroup.last_seen_at >= week_ago,
            SuiteRun.environment_id == prod_env.id if prod_env else True
        )
        .order_by(desc(AlertGroup.repeat_count))
        .all()
    )

    # Deduplikacja — max 1 per business_rule
    seen_rules = set()
    top_alerts = []
    for ag in top_alerts_raw:
        if ag.business_rule not in seen_rules:
            seen_rules.add(ag.business_rule)
            top_alerts.append(ag)
        if len(top_alerts) >= 10:
            break

    # ── Ostatnie runy (10) ────────────────────────────────────────────────────
    recent_runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .limit(10)
        .all()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recent_runs": recent_runs,
        # Liczniki
        "active_alerts": active_alerts,
        "backlog_alerts": backlog_alerts,
        "new_today": new_today,
        "scenarios_24h": scenarios_24h,
        "failed_24h": failed_24h,
        # Trend
        "alerts_this_week": alerts_this_week,
        "trend_pct": abs(trend_pct),
        "trend_up": trend_up,
        # Top błędów
        "top_alerts": top_alerts,
    })


@router.get("/dashboard/runs-table")
async def dashboard_runs_table(request: Request, db: Session = Depends(get_db)):
    recent_runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .limit(10)
        .all()
    )
    return templates.TemplateResponse("dashboard_runs_table.html", {
        "request": request,
        "recent_runs": recent_runs,
    })
