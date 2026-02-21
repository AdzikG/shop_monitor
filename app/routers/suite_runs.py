from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
import html
import re
from pathlib import Path

from database import get_db
from app.models.suite_run import SuiteRun
from app.models.run import ScenarioRun
from app.templates import templates

router = APIRouter(tags=["suite_runs"])


@router.get("/suite-runs")
async def suite_runs_list(request: Request, db: Session = Depends(get_db)):
    """Lista wszystkich suite runs."""
    runs = (
        db.query(SuiteRun)
        .order_by(desc(SuiteRun.started_at))
        .limit(100)
        .all()
    )
    return templates.TemplateResponse("suite_runs_list.html", {
        "request": request,
        "runs": runs,
    })


@router.get("/suite-runs/{suite_run_id}")
async def suite_run_detail(suite_run_id: int, request: Request, db: Session = Depends(get_db)):
    """Szczegoly suite run — lista scenariuszy i alert groups."""
    suite_run = db.query(SuiteRun).filter(SuiteRun.id == suite_run_id).first()
    if not suite_run:
        raise HTTPException(status_code=404, detail="Suite run not found")
    
    scenario_runs = (
        db.query(ScenarioRun)
        .filter(ScenarioRun.suite_run_id == suite_run_id)
        .order_by(ScenarioRun.started_at)
        .all()
    )
    
    alert_groups = []
    for group in suite_run.alert_groups:
        try:
            scenario_ids = json.loads(group.scenario_ids) if group.scenario_ids else []
        except:
            scenario_ids = []
        
        alert_groups.append({
            'id': group.id,
            'business_rule': group.business_rule,
            'title': group.title,
            'alert_type': group.alert_type,
            'occurrence_count': group.occurrence_count,
            'scenario_ids': scenario_ids,
        })
    
    return templates.TemplateResponse("suite_run_detail.html", {
        "request": request,
        "suite_run": suite_run,
        "scenario_runs": scenario_runs,
        "alert_groups": alert_groups,
    })


@router.get("/suite-runs/{suite_run_id}/logs", response_class=HTMLResponse)
async def suite_run_logs(suite_run_id: int):
    """Zwraca logi suite run."""
    
    log_file = Path(f"logs/suite_run_{suite_run_id}.log")
    
    if not log_file.exists():
        return "<div style='padding: 2rem; text-align: center; color: var(--text-secondary);'>No logs available</div>"
    
    try:
        content = log_file.read_text(encoding='utf-8')
        
        # Escape HTML
        escaped = html.escape(content)
        
        # Użyj <pre> z white-space: pre-wrap zamiast zamiany na <br>
        # To zachowa WSZYSTKIE białe znaki i nowe linie automatycznie
        html_content = f"""
        <pre style='margin: 0; padding: 1rem; background: var(--bg-dark); color: var(--text-primary); 
                    font-size: 11px; line-height: 1.6; overflow-x: auto; 
                    font-family: "IBM Plex Mono", monospace;
                    white-space: pre-wrap; word-wrap: break-word;'>{escaped}</pre>
        """
        return html_content
    except Exception as e:
        return f"<div style='padding: 2rem; color: var(--accent-red);'>Error loading logs: {e}</div>"