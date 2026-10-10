import os
import re
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.database.repository import VideoRepository
from backend.app.schemas.video import VideoResponse
from backend.app.api.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/videos", tags=["Videos"])

def _resolve_safe_file_path(base_dir: Path, file_path_str: str) -> Path:
    """
    Prevents directory traversal attacks by verifying the resolved file resides
    within the configured base directory.
    """
    try:
        p = Path(file_path_str)
        if not p.is_absolute():
            resolved = (base_dir / p).resolve()
        else:
            resolved = p.resolve()
        base_resolved = base_dir.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: invalid file path")
        return resolved
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed file path")

@router.get("", response_model=List[VideoResponse])
async def list_videos(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    video_repo = VideoRepository(db)
    videos = await video_repo.list_videos(limit=limit, offset=offset)
    
    return [
        VideoResponse(
            id=v.id,
            job_id=v.job_id,
            title=v.title,
            duration=v.duration,
            width=v.width,
            height=v.height,
            fps=v.fps,
            file_size=v.file_size,
            created_at=v.created_at,
            download_url=f"/api/videos/{v.id}/download",
            thumbnail_url=f"/api/videos/{v.id}/thumbnail" if v.thumbnail_path else None
        )
        for v in videos
    ]

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    video_repo = VideoRepository(db)
    v = await video_repo.get_video_by_id(video_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    return VideoResponse(
        id=v.id,
        job_id=v.job_id,
        title=v.title,
        duration=v.duration,
        width=v.width,
        height=v.height,
        fps=v.fps,
        file_size=v.file_size,
        created_at=v.created_at,
        download_url=f"/api/videos/{v.id}/download",
        thumbnail_url=f"/api/videos/{v.id}/thumbnail" if v.thumbnail_path else None
    )

@router.get("/{video_id}/download")
async def download_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    """
    Download endpoint streaming the generated MP4 file.
    Does not load the file into application memory.
    """
    video_repo = VideoRepository(db)
    v = await video_repo.get_video_by_id(video_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    file_path = _resolve_safe_file_path(settings.OUTPUT_DIR, v.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found on disk")

    clean_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', f"{v.title}_{v.id[:6]}.mp4")
    return FileResponse(
        path=str(file_path),
        filename=clean_filename,
        media_type="video/mp4",
        content_disposition_type="attachment"
    )

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    """
    Supports HTTP Range requests for seamless HTML5 in-browser video playback.
    """
    video_repo = VideoRepository(db)
    v = await video_repo.get_video_by_id(video_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    file_path = _resolve_safe_file_path(settings.OUTPUT_DIR, v.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found on disk")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(str(file_path), media_type="video/mp4")

    # Parse byte range
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return FileResponse(str(file_path), media_type="video/mp4")

    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    if end >= file_size:
        end = file_size - 1

    if start >= file_size or start > end:
        raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, detail="Invalid byte range")

    chunk_size = (end - start) + 1

    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_left = chunk_size
            while bytes_left > 0:
                read_bytes = min(bytes_left, 1024 * 64)
                data = f.read(read_bytes)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)

@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns thumbnail image for preview cards.
    """
    video_repo = VideoRepository(db)
    v = await video_repo.get_video_by_id(video_id)
    if not v or not v.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    thumb_path = _resolve_safe_file_path(settings.OUTPUT_DIR, v.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file not found")

    return FileResponse(str(thumb_path), media_type="image/jpeg")

@router.delete("/{video_id}", status_code=status.HTTP_200_OK)
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user)
):
    video_repo = VideoRepository(db)
    v = await video_repo.get_video_by_id(video_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    deleted_files = []
    # 1. Delete main video file from VPS disk
    if v.file_path:
        try:
            fp = _resolve_safe_file_path(settings.OUTPUT_DIR, v.file_path)
            if fp.exists():
                fp.unlink()
                deleted_files.append(str(fp.name))
        except Exception:
            pass

    # 2. Delete thumbnail file from VPS disk
    if v.thumbnail_path:
        try:
            tp = _resolve_safe_file_path(settings.OUTPUT_DIR, v.thumbnail_path)
            if tp.exists():
                tp.unlink()
                deleted_files.append(str(tp.name))
        except Exception:
            pass

    # 3. Clean up associated subtitle/audio stems from outputs
    try:
        if v.file_path:
            base_stem = Path(v.file_path).stem
            for extra in settings.OUTPUT_DIR.glob(f"{base_stem}*"):
                if extra.is_file() and extra.exists():
                    extra.unlink()
                    deleted_files.append(str(extra.name))
    except Exception:
        pass

    # 4. Delete video record from SQLite database
    await video_repo.delete_video(video_id)
    return {
        "status": "success",
        "message": f"Video {video_id} permanently deleted from VPS storage and database.",
        "deleted_files": deleted_files
    }
