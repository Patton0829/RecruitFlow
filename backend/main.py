from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import UPLOAD_DIR
from .database import init_db
from .routers import candidates, dashboard, reminders, resumes
from .services.reminder_service import create_scheduler


app = FastAPI(title="RecruitFlow AI｜招聘流程提效助手", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler


@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(candidates.router, prefix="/api", tags=["candidates"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["reminders"])
