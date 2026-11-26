import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_dashboard,
    admin_duty_records,
    admin_master_data,
    admin_message_templates,
    admin_statistics,
    admin_system_health,
    admin_users,
    auth,
    cp_complaints,
    l1_bus_lookup,
    l1_complaints,
    l1_daily_records,
    l1_dashboard,
    l1_recommendations,
    l2_cases,
    l2_dashboard,
    l2_recommendations,
    portal_signup,
)
from app.core.config import settings
from app.core.csrf import csrf_guard
from app.services import health_check_service

settings.validate_for_startup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    checks = asyncio.create_task(health_check_service.health_check_loop(app))
    yield
    checks.cancel()


app = FastAPI(title="SPRPTA System API", lifespan=lifespan)

app.middleware("http")(csrf_guard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(portal_signup.router)
app.include_router(cp_complaints.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_system_health.router)
app.include_router(admin_users.router)
app.include_router(admin_duty_records.router)
app.include_router(admin_master_data.router)
app.include_router(admin_message_templates.router)
app.include_router(admin_statistics.router)
app.include_router(l1_bus_lookup.router)
app.include_router(l1_dashboard.router)
app.include_router(l1_daily_records.router)
app.include_router(l1_complaints.router)
app.include_router(l1_recommendations.router)
app.include_router(l2_dashboard.router)
app.include_router(l2_cases.router)
app.include_router(l2_recommendations.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sprpta-api"}
