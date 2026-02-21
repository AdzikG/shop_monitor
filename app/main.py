from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import dashboard, suite_runs, alerts, execute, scenarios, alert_configs

app = FastAPI(title="Shop Monitor")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routery
app.include_router(dashboard.router)
app.include_router(suite_runs.router)
app.include_router(alerts.router)
app.include_router(execute.router)
app.include_router(scenarios.router)
app.include_router(alert_configs.router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")
