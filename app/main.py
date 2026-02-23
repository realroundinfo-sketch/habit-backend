from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.config import get_settings
from app.database import init_db
from app.routes import auth, checkins, habits, goals, analytics_routes, events

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal Habit and Performance Intelligence Platform",
    lifespan=lifespan,
)

# CORS — use CORS_ORIGINS env (e.g. "*" or "https://yourapp.vercel.app,https://yourapp.up.railway.app")
_origins = settings.CORS_ORIGINS.strip()
_cors_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)},
    )


# Routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(checkins.router, prefix="/api/v1")
app.include_router(habits.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(analytics_routes.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
