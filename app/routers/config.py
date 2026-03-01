from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from database import get_db
from app.models.dictionary import Dictionary
from app.models.flag_definition import FlagDefinition
from app.models.alert_config import AlertConfig
from app.models.suite import Suite
from app.models.scenario import Scenario
from app.models.scheduled_job import ScheduledJob
from app.templates import templates

router = APIRouter(tags=["config"])


@router.get("/config")
async def config_hub(request: Request, db: Session = Depends(get_db)):
    dict_count = db.query(Dictionary).count()
    flag_count = db.query(FlagDefinition).count()
    alert_config_count = db.query(AlertConfig).count()
    suite_count = db.query(Suite).filter_by(is_active=True).count()
    scenario_count = db.query(Scenario).filter_by(is_active=True).count()
    scheduler_count = db.query(ScheduledJob).filter_by(is_enabled=True).count()

    return templates.TemplateResponse("config.html", {
        "request": request,
        "dict_count": dict_count,
        "flag_count": flag_count,
        "alert_config_count": alert_config_count,
        "suite_count": suite_count,
        "scenario_count": scenario_count,
        "scheduler_count": scheduler_count,
    })