from urllib.parse import urlparse

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.api_error import ApiError
from app.models.api_error_exclusion import ApiErrorExclusion
from app.templates import templates

router = APIRouter(tags=["api_error_exclusions"])


@router.get("/api-error-exclusions")
async def exclusions_list(request: Request, db: Session = Depends(get_db)):
    exclusions = db.query(ApiErrorExclusion).order_by(ApiErrorExclusion.id.desc()).all()
    return templates.TemplateResponse("api_error_exclusions_list.html", {
        "request": request,
        "exclusions": exclusions,
    })


@router.post("/api-error-exclusions/from-error/{api_error_id}")
async def create_from_error(api_error_id: int, db: Session = Depends(get_db)):
    err = db.query(ApiError).filter_by(id=api_error_id).first()
    if not err:
        raise HTTPException(status_code=404, detail="ApiError not found")

    parsed = urlparse(err.endpoint)
    pattern = parsed.path  # path only, no query string, no domain

    exclusion = ApiErrorExclusion(
        endpoint_pattern=pattern,
        status_code=err.status_code,
        response_body_pattern=None,
    )
    db.add(exclusion)
    db.commit()

    run = err.run
    return RedirectResponse(
        url=f"/suite-runs/{run.suite_run_id}/{run.id}",
        status_code=303,
    )


@router.post("/api-error-exclusions/{exclusion_id}/delete")
async def delete_exclusion(exclusion_id: int, db: Session = Depends(get_db)):
    excl = db.query(ApiErrorExclusion).filter_by(id=exclusion_id).first()
    if not excl:
        raise HTTPException(status_code=404, detail="Exclusion not found")
    db.delete(excl)
    db.commit()
    return RedirectResponse(url="/api-error-exclusions", status_code=303)
