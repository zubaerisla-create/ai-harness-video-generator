import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "AI Story Video Generation Harness",
        "version": "1.0.0"
    }

@app.get("/")
@app.get("/dashboard")
async def dashboard_index():
    from fastapi.responses import FileResponse
    from pathlib import Path
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file), media_type="text/html")
    return {
        "service": "AI Story Video Generation Harness",
        "status": "operational",
        "docs_url": "/docs"
    }

