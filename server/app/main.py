from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes.health import router as health_router
from app.api.routes.amqp_test import router as amqp_test_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes import files

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(amqp_test_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(files.router, prefix=settings.api_prefix)

@app.get("/")
async def root():
    return {
        "message": "Welcome to FlowPilot API",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }