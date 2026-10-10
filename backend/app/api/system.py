import shutil
import psutil
import httpx
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.models.database import VideoJob, Video
from backend.app.schemas.video import SystemResources, SystemStats
from backend.app.api.auth import get_optional_user

router = APIRouter(prefix="/api/system", tags=["System"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Story Video Generation Harness",
        "version": "1.0.0"
    }

@router.get("/resources", response_model=SystemResources)
async def get_system_resources(user=Depends(get_optional_user)):
    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Disk
    total, used, free = shutil.disk_usage(settings.OUTPUT_DIR)
    
    # Check Ollama
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = res.status_code == 200
    except Exception:
        ollama_ok = False

    # Check ComfyUI
    comfyui_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.COMFYUI_URL}/system_stats")
            comfyui_ok = res.status_code == 200
    except Exception:
        comfyui_ok = False

    # Check FFmpeg
    ffmpeg_ok = shutil.which("ffmpeg") is not None

    return SystemResources(
        cpu_percent=psutil.cpu_percent(interval=None),
        cpu_count=psutil.cpu_count(logical=True),
        ram_total_gb=round(mem.total / (1024**3), 2),
        ram_used_gb=round(mem.used / (1024**3), 2),
        ram_available_gb=round(mem.available / (1024**3), 2),
        swap_total_gb=round(swap.total / (1024**3), 2),
        swap_used_gb=round(swap.used / (1024**3), 2),
        disk_total_gb=round(total / (1024**3), 2),
        disk_used_gb=round(used / (1024**3), 2),
        disk_free_gb=round(free / (1024**3), 2),
        ollama_running=ollama_ok,
        comfyui_running=comfyui_ok,
        ffmpeg_installed=ffmpeg_ok
    )

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    # Video count
    res_videos = await db.execute(select(func.count(Video.id)))
    total_videos = res_videos.scalar_one() or 0

    # Job counts
    res_completed = await db.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "completed"))
    completed_jobs = res_completed.scalar_one() or 0

    res_failed = await db.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "failed"))
    failed_jobs = res_failed.scalar_one() or 0

    res_pending = await db.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "pending"))
    pending_jobs = res_pending.scalar_one() or 0

    res_proc = await db.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "processing"))
    processing_jobs = res_proc.scalar_one() or 0

    # Average render duration from completed videos
    res_avg = await db.execute(select(func.avg(Video.duration)))
    avg_render_dur = res_avg.scalar_one() or 0.0

    # Disk free
    _, _, free = shutil.disk_usage(settings.OUTPUT_DIR)
    free_gb = round(free / (1024**3), 2)

    # Estimate daily throughput based on completed jobs or default baseline
    # Default baseline for 2 vCPU VPS (approx 2.5 minutes per 120s video with local storyboard + Piper) = ~500/day
    est_daily = round(86400.0 / 180.0, 1) if completed_jobs == 0 else round(86400.0 / max(60.0, avg_render_dur), 1)

    return SystemStats(
        total_videos=total_videos,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        pending_jobs=pending_jobs,
        processing_jobs=processing_jobs,
        avg_render_time_seconds=round(float(avg_render_dur), 1),
        disk_free_gb=free_gb,
        estimated_daily_throughput=est_daily
    )

@router.get("/autopilot")
async def get_autopilot_status():
    from backend.app.services.auto_pilot import auto_pilot
    return await auto_pilot.get_status()

@router.post("/autopilot/toggle")
async def toggle_autopilot(payload: Dict[str, Any]):
    from backend.app.services.auto_pilot import auto_pilot
    enabled = payload.get("enabled", True)
    daily_target = int(payload.get("daily_target", 25))
    auto_pilot.set_config(enabled=enabled, target=daily_target)
    return await auto_pilot.get_status()
