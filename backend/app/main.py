from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "sprpta-api"}
