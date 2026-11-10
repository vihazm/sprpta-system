from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin_dashboard, admin_users, auth
from app.core.config import settings
from app.core.csrf import csrf_guard

settings.validate_for_startup()

app = FastAPI(title="SPRPTA System API")

app.middleware("http")(csrf_guard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_users.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sprpta-api"}
