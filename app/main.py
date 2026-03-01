from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import (
    dashboard, suite_runs, alerts, execute, scenarios,
    alert_configs, suites, auth_router, dictionaries, flags, config
)
from app.routers import scheduler_router
from app.routers import api_error_exclusions
from app import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start
    scheduler.start()
    yield
    # Stop
    scheduler.stop()


app = FastAPI(title="Shop Monitor", lifespan=lifespan)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routery
app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(suite_runs.router)
app.include_router(alerts.router)
app.include_router(execute.router)
app.include_router(scenarios.router)
app.include_router(alert_configs.router)
app.include_router(suites.router)
app.include_router(dictionaries.router)
app.include_router(flags.router)
app.include_router(config.router)
app.include_router(scheduler_router.router)
app.include_router(api_error_exclusions.router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")
