import json
import shutil
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.database.repository import JobRepository
from backend.app.schemas.video import JobCreateRequest, JobResponse, SceneResponse
from backend.app.api.auth import get_optional_user

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body

logger = logging.getLogger("ai_harness.api.jobs")
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_job(
    request: Optional[JobCreateRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    if request is None:
        request = JobCreateRequest()
    # Check free disk space before admitting job
    total, used, free = shutil.disk_usage(settings.OUTPUT_DIR)
    free_gb = free / (1024 ** 3)
    if free_gb < settings.MIN_DISK_FREE_GB:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=f"Server storage low ({free_gb:.1f} GB free). Minimum required is {settings.MIN_DISK_FREE_GB} GB."
        )

    job_repo = JobRepository(db)
    job_data = {
        "prompt": request.prompt.strip(),
        "style": request.style.lower(),
        "requested_duration": request.requested_duration,
        "requested_resolution": request.requested_resolution,
        "aspect_ratio": request.aspect_ratio,
        "enable_narration": request.enable_narration,
        "enable_subtitles": request.enable_subtitles,
        "enable_bgm": request.enable_bgm,
        "status": "pending",
        "progress": 0,
        "stage": "queued"
    }
    job = await job_repo.create_job(job_data)
    
    # Return formatted response
    return _format_job_response(job)

@router.get("", response_model=List[JobResponse])
@router.get("/", response_model=List[JobResponse], include_in_schema=False)
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    job_repo = JobRepository(db)
    jobs = await job_repo.list_jobs(limit=limit, offset=offset, status=status_filter)
    return [_format_job_response(j) for j in jobs]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    job_repo = JobRepository(db)
    job = await job_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _format_job_response(job)

@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    job_repo = JobRepository(db)
    job = await job_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    if job.status not in ["failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry a job currently in '{job.status}' status"
        )

    updated = await job_repo.update_job_status(
        job_id=job_id,
        status="pending",
        progress=0,
        stage="queued",
        error_message=None
    )
    return _format_job_response(updated)

@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    job_repo = JobRepository(db)
    job = await job_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in '{job.status}' status"
        )

    updated = await job_repo.update_job_status(
        job_id=job_id,
        status="cancelled",
        stage="cancelled",
        error_message="User requested cancellation"
    )
    return _format_job_response(updated)

def _format_job_response(job) -> JobResponse:
    bench_data = None
    if job.benchmark_data:
        try:
            bench_data = json.loads(job.benchmark_data)
        except Exception:
            pass

    scenes_list = []
    if "scenes" in job.__dict__ and job.__dict__["scenes"]:
        for sc in job.__dict__["scenes"]:
            scenes_list.append(SceneResponse(
                id=sc.id,
                sequence_number=sc.sequence_number,
                narration_text=sc.narration_text,
                visual_prompt=sc.visual_prompt,
                visual_backend=sc.visual_backend,
                image_path=sc.image_path,
                audio_path=sc.audio_path,
                duration=sc.duration,
                status=sc.status
            ))

    video_dict = None
    v = job.__dict__.get("video")
    if v:
        video_dict = {
            "id": v.id,
            "job_id": v.job_id,
            "title": v.title,
            "duration": v.duration,
            "width": v.width,
            "height": v.height,
            "fps": v.fps,
            "file_size": v.file_size,
            "created_at": v.created_at,
            "download_url": f"/api/videos/{v.id}/download",
            "thumbnail_url": f"/api/videos/{v.id}/thumbnail" if v.thumbnail_path else None
        }

    return JobResponse(
        id=job.id,
        prompt=job.prompt,
        style=job.style,
        requested_duration=job.requested_duration,
        requested_resolution=job.requested_resolution,
        aspect_ratio=job.aspect_ratio,
        enable_narration=job.enable_narration,
        enable_subtitles=job.enable_subtitles,
        enable_bgm=job.enable_bgm,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        video=video_dict,
        scenes=scenes_list,
        benchmark_data=bench_data,
        facebook_video_id=job.facebook_video_id,
        facebook_post_id=job.facebook_post_id,
        scheduled_publish_time=job.scheduled_publish_time,
        published_at=job.published_at,
        caption=job.caption,
        hashtags=job.hashtags,
        upload_error=job.upload_error
    )
