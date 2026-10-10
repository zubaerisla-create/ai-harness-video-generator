import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.config import settings
from backend.app.database.session import init_db, AsyncSessionLocal
from backend.app.database.repository import UserRepository
from backend.app.api.auth import router as auth_router, get_password_hash
from backend.app.api.jobs import router as jobs_router
from backend.app.api.videos import router as videos_router
from backend.app.api.system import router as system_router
from backend.app.workers.queue import worker_service
from backend.app.services.auto_pilot import auto_pilot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_harness")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Story Harness database...")
    await init_db()

    # Ensure admin user is seeded in database
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        admin = await user_repo.get_by_username(settings.ADMIN_USERNAME)
        if not admin:
            hashed = get_password_hash(settings.ADMIN_PASSWORD)
            await user_repo.create_user(settings.ADMIN_USERNAME, hashed)
            logger.info(f"Default admin user '{settings.ADMIN_USERNAME}' initialized.")

    # Start background job worker and 24/7 auto pilot
    await worker_service.start()
    await auto_pilot.start()
    logger.info("AI Story Video Generation Harness ready with Auto-Pilot enabled.")
    
    yield
    
    logger.info("Shutting down AI Story Harness...")
    await auto_pilot.stop()
    await worker_service.stop()

app = FastAPI(
    title="AI Story Video Generation Harness",
    description="Production-grade self-hosted automated short story video creation engine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows web dashboard and API access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(videos_router)
app.include_router(system_router)

from backend.app.database.session import get_db
from backend.app.api.system import get_system_stats, get_system_resources
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "AI Story Video Generation Harness",
        "version": "1.0.0"
    }

@app.get("/api/stats")
async def api_stats_alias(db: AsyncSession = Depends(get_db)):
    return await get_system_stats(db=db)

@app.get("/api/resources")
async def api_resources_alias():
    return await get_system_resources()

@app.get("/")
@app.get("/dashboard")
async def dashboard_index(request: Request):
    """
    Redirect browser traffic on port 8000 directly to the Next.js web application on port 80.
    """
    host = request.headers.get("host", "").split(":")[0] or "31.97.180.176"
    return RedirectResponse(url=f"http://{host}/", status_code=307)

@app.get("/{full_path:path}")
async def catchall_redirect(request: Request, full_path: str):
    """
    Redirect non-API routes (e.g. /vault, /VAULT, /studio, /queue, /telemetry) from port 8000 to port 80.
    """
    # Allow Swagger docs, OpenAPI spec, and direct API endpoints to pass through
    if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "favicon.ico"]:
        raise HTTPException(status_code=404, detail="Not Found")
    
    clean_path = full_path.lower().strip("/")
    host = request.headers.get("host", "").split(":")[0] or "31.97.180.176"
    return RedirectResponse(url=f"http://{host}/{clean_path}", status_code=307)

