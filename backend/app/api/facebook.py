import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.database.repository import JobRepository, DailyPublicationRepository
from backend.app.services.facebook_publisher import facebook_publisher
from backend.app.services.auto_pilot import auto_pilot
from backend.app.workers.queue import worker_service
from backend.app.api.auth import get_optional_user

logger = logging.getLogger("ai_harness.api.facebook")
router = APIRouter(prefix="/api/facebook", tags=["Facebook Publishing"])

@router.get("/status")
async def get_facebook_status():
    """
    Returns live connectivity status with Facebook Page Graph API,
    token validity, today's publication quota (Asia/Dhaka), and slot schedules.
    Never exposes raw access tokens.
    """
    page_info = await facebook_publisher.verify_page_access()
    scheduler_status = await auto_pilot.get_status()

    return {
        "page_connected": page_info.get("valid", False),
        "page_id": page_info.get("page_id", settings.META_PAGE_ID),
        "page_name": page_info.get("page_name", "Unknown"),
        "page_link": page_info.get("link"),
        "token_masked": page_info.get("token_masked"),
        "publishing_enabled": settings.FACEBOOK_PUBLISHING_ENABLED,
        "dry_run": settings.DRY_RUN,
        "pilot_mode": settings.PILOT_ONE_POST_ROLLOUT,
        "pilot_max_live_posts": settings.PILOT_MAX_LIVE_POSTS,
        "timezone": scheduler_status.get("timezone"),
        "local_time": scheduler_status.get("local_time"),
        "local_date": scheduler_status.get("local_date"),
        "daily_target": scheduler_status.get("daily_target"),
        "published_today": scheduler_status.get("published_today"),
        "quota_remaining": scheduler_status.get("quota_remaining"),
        "quota_met": scheduler_status.get("quota_met"),
        "next_slot": scheduler_status.get("next_slot"),
        "slots": scheduler_status.get("slots"),
        "has_ready_video": scheduler_status.get("has_ready_video")
    }

@router.get("/daily-summary")
async def get_daily_summary(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive daily publishing summary report:
    - Videos planned, rendered, and published today
    - Quota status (target: 5/day)
    - Slot fulfillment breakdown
    - Any failed upload attempts and safe error messages
    """
    scheduler_status = await auto_pilot.get_status()
    local_date = scheduler_status.get("local_date")

    daily_repo = DailyPublicationRepository(db)
    daily_rec = await daily_repo.get_or_create_daily(local_date, settings.TIMEZONE)

    slots_fulfilled = json.loads(daily_rec.slots_fulfilled or "[]")
    published_video_ids = json.loads(daily_rec.video_ids or "[]")

    job_repo = JobRepository(db)
    ready_jobs = await job_repo.list_jobs(limit=10, status="ready")
    failed_jobs = await job_repo.list_jobs(limit=10, status="failed")

    return {
        "date": local_date,
        "timezone": settings.TIMEZONE,
        "daily_target": settings.MAX_DAILY_PUBLISHED_VIDEOS,
        "published_count": daily_rec.published_count,
        "quota_met": daily_rec.published_count >= settings.MAX_DAILY_PUBLISHED_VIDEOS,
        "slots_fulfilled": slots_fulfilled,
        "published_video_ids": published_video_ids,
        "ready_for_next_slot": len(ready_jobs),
        "recent_failures_count": len(failed_jobs),
        "slots_detail": scheduler_status.get("slots"),
        "dry_run_mode": settings.DRY_RUN
    }

@router.post("/publish-now/{job_id}")
async def publish_now(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    """
    Manually triggers immediate Facebook publishing for a specific ready or completed video job.
    Enforces QA gate, token authentication, and the 5-per-day quota limit.
    """
    job_repo = JobRepository(db)
    job = await job_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.facebook_video_id and job.status == "published":
        return {
            "status": "already_published",
            "job_id": job_id,
            "facebook_video_id": job.facebook_video_id,
            "message": "This video has already been published to Facebook."
        }

    # Check daily quota
    scheduler_status = await auto_pilot.get_status()
    if scheduler_status.get("published_today", 0) >= settings.MAX_DAILY_PUBLISHED_VIDEOS:
        raise HTTPException(
            status_code=429,
            detail=f"Daily publishing limit ({settings.MAX_DAILY_PUBLISHED_VIDEOS} videos) has been reached for today."
        )

    # Trigger publication through the orchestrator
    success = await worker_service.orchestrator.publish_job(job_id)
    if not success:
        refreshed_job = await job_repo.get_job_by_id(job_id)
        err = refreshed_job.upload_error if refreshed_job else "Unknown publication error"
        raise HTTPException(status_code=500, detail=f"Failed to publish to Facebook: {err}")

    updated_job = await job_repo.get_job_by_id(job_id)
    return {
        "status": "published",
        "job_id": job_id,
        "facebook_video_id": updated_job.facebook_video_id if updated_job else None,
        "published_at": updated_job.published_at if updated_job else None,
        "message": "Video successfully published to Facebook Page."
    }

@router.post("/dry-run")
async def toggle_dry_run(payload: Dict[str, Any], user=Depends(get_optional_user)):
    """
    Enables or disables dry-run mode for testing without calling live Facebook API.
    """
    dry_run = bool(payload.get("enabled", True))
    settings.DRY_RUN = dry_run
    logger.info(f"DRY_RUN mode updated to: {dry_run}")
    return {"dry_run": settings.DRY_RUN, "message": f"Dry-run mode is now {'enabled' if dry_run else 'disabled'}"}

@router.post("/emergency-kill-switch")
async def emergency_kill_switch(user=Depends(get_optional_user)):
    """
    Emergency kill switch: Immediately forces DRY_RUN=True and FACEBOOK_PUBLISHING_ENABLED=False
    in memory. Instantly halts all live uploads (scheduled and manual) with zero server restart.
    """
    settings.FACEBOOK_PUBLISHING_ENABLED = False
    settings.DRY_RUN = True
    logger.critical("EMERGENCY KILL SWITCH ENGAGED: Live Facebook publishing immediately halted.")
    return {
        "status": "killed",
        "facebook_publishing_enabled": False,
        "dry_run": True,
        "message": "Emergency kill switch engaged. All live Facebook publications are immediately blocked."
    }

@router.post("/toggle-publishing")
async def toggle_publishing(payload: Dict[str, Any], user=Depends(get_optional_user)):
    """
    Toggles live Facebook publishing on or off in memory.
    """
    enabled = bool(payload.get("enabled", False))
    settings.FACEBOOK_PUBLISHING_ENABLED = enabled
    logger.info(f"FACEBOOK_PUBLISHING_ENABLED updated to: {enabled}")
    return {
        "facebook_publishing_enabled": settings.FACEBOOK_PUBLISHING_ENABLED,
        "dry_run": settings.DRY_RUN,
        "message": f"Facebook live publishing is now {'enabled' if enabled else 'disabled'}"
    }

