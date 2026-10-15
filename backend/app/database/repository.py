from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, delete, desc, func, not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import json
from backend.app.models.database import VideoJob, Video, Scene, User, DailyPublication

class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, job_data: Dict[str, Any]) -> VideoJob:
        job = VideoJob(**job_data)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job_by_id(self, job_id: str) -> Optional[VideoJob]:
        stmt = (
            select(VideoJob)
            .where(VideoJob.id == job_id)
            .options(selectinload(VideoJob.video), selectinload(VideoJob.scenes))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[VideoJob]:
        stmt = select(VideoJob).options(selectinload(VideoJob.video)).order_by(desc(VideoJob.created_at)).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(VideoJob.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
        benchmark_data: Optional[str] = None,
        facebook_video_id: Optional[str] = None,
        facebook_post_id: Optional[str] = None,
        published_at: Optional[datetime] = None,
        scheduled_publish_time: Optional[datetime] = None,
        upload_error: Optional[str] = None,
        upload_attempts: Optional[int] = None,
        caption: Optional[str] = None,
        hashtags: Optional[str] = None,
        sources_used: Optional[str] = None
    ) -> Optional[VideoJob]:
        values: Dict[str, Any] = {"status": status}
        if progress is not None:
            values["progress"] = progress
        if stage is not None:
            values["stage"] = stage
        if error_message is not None:
            values["error_message"] = error_message
        if benchmark_data is not None:
            values["benchmark_data"] = benchmark_data
        if facebook_video_id is not None:
            values["facebook_video_id"] = facebook_video_id
        if facebook_post_id is not None:
            values["facebook_post_id"] = facebook_post_id
        if published_at is not None:
            values["published_at"] = published_at
        if scheduled_publish_time is not None:
            values["scheduled_publish_time"] = scheduled_publish_time
        if upload_error is not None:
            values["upload_error"] = upload_error
        if upload_attempts is not None:
            values["upload_attempts"] = upload_attempts
        if caption is not None:
            values["caption"] = caption
        if hashtags is not None:
            values["hashtags"] = hashtags
        if sources_used is not None:
            values["sources_used"] = sources_used

        if status == "processing":
            values["started_at"] = datetime.utcnow()
        elif status in ["completed", "published", "failed", "cancelled"]:
            values["completed_at"] = datetime.utcnow()

        stmt = update(VideoJob).where(VideoJob.id == job_id).values(**values).execution_options(synchronize_session="fetch")
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_job_by_id(job_id)

    async def get_next_pending_job(self) -> Optional[VideoJob]:
        stmt = (
            select(VideoJob)
            .where(VideoJob.status == "pending")
            .order_by(VideoJob.created_at)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_running_jobs_count(self) -> int:
        stmt = select(func.count(VideoJob.id)).where(VideoJob.status.in_(["processing", "uploading"]))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_ready_job_for_slot(self) -> Optional[VideoJob]:
        """Returns the oldest completed/ready video that has not yet been published to Facebook."""
        stmt = (
            select(VideoJob)
            .where(
                VideoJob.status.in_(["ready", "completed"]),
                VideoJob.facebook_video_id.is_(None)
            )
            .options(selectinload(VideoJob.video))
            .order_by(VideoJob.created_at)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_retryable_upload_jobs(self) -> List[VideoJob]:
        """Finds jobs waiting for upload retry after transient error."""
        stmt = (
            select(VideoJob)
            .where(
                VideoJob.status == "retry_pending",
                VideoJob.upload_attempts < 2
            )
            .options(selectinload(VideoJob.video))
            .limit(5)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def recover_stale_jobs(self) -> int:
        """Recovers interrupted jobs on server restart without duplicate publishing."""
        stmt1 = (
            update(VideoJob)
            .where(VideoJob.status == "processing")
            .values(
                status="failed",
                error_message="Job interrupted due to server/worker restart. Can be retried.",
                completed_at=datetime.utcnow()
            )
        )
        # Any job interrupted in 'uploading' should become 'retry_pending' to verify state
        stmt2 = (
            update(VideoJob)
            .where(VideoJob.status == "uploading")
            .values(
                status="retry_pending",
                upload_error="Upload interrupted by server restart. Scheduled for verification."
            )
        )
        r1 = await self.session.execute(stmt1)
        r2 = await self.session.execute(stmt2)
        await self.session.commit()
        return r1.rowcount + r2.rowcount

class VideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_video(self, video_data: Dict[str, Any]) -> Video:
        video = Video(**video_data)
        self.session.add(video)
        await self.session.commit()
        await self.session.refresh(video)
        return video

    async def get_video_by_id(self, video_id: str) -> Optional[Video]:
        stmt = select(Video).where(Video.id == video_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_video_by_job_id(self, job_id: str) -> Optional[Video]:
        stmt = select(Video).where(Video.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_videos(self, limit: int = 50, offset: int = 0) -> List[Video]:
        stmt = select(Video).order_by(desc(Video.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_video(self, video_id: str) -> bool:
        stmt = delete(Video).where(Video.id == video_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

class SceneRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scenes(self, scenes_data: List[Dict[str, Any]]) -> List[Scene]:
        scenes = [Scene(**item) for item in scenes_data]
        self.session.add_all(scenes)
        await self.session.commit()
        return scenes

    async def get_scenes_by_job_id(self, job_id: str) -> List[Scene]:
        stmt = select(Scene).where(Scene.job_id == job_id).order_by(Scene.sequence_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_scene(self, scene_id: str, values: Dict[str, Any]) -> Optional[Scene]:
        stmt = update(Scene).where(Scene.id == scene_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()
        stmt_select = select(Scene).where(Scene.id == scene_id)
        res = await self.session.execute(stmt_select)
        return res.scalar_one_or_none()

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, username: str, hashed_password: str) -> User:
        user = User(username=username, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

class DailyPublicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_daily(self, local_date: str, timezone: str = "Asia/Dhaka") -> DailyPublication:
        stmt = select(DailyPublication).where(DailyPublication.local_date == local_date)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            record = DailyPublication(
                local_date=local_date,
                timezone=timezone,
                published_count=0,
                slots_fulfilled="[]",
                video_ids="[]"
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def record_publication(self, local_date: str, slot: str, video_id: str, timezone: str = "Asia/Dhaka") -> DailyPublication:
        record = await self.get_or_create_daily(local_date, timezone)
        slots = json.loads(record.slots_fulfilled or "[]")
        if slot not in slots:
            slots.append(slot)
        vids = json.loads(record.video_ids or "[]")
        if video_id not in vids:
            vids.append(video_id)
        
        record.published_count = len(vids)
        record.slots_fulfilled = json.dumps(slots)
        record.video_ids = json.dumps(vids)
        record.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_today_count(self, local_date: str) -> int:
        record = await self.get_or_create_daily(local_date)
        return record.published_count

    async def get_live_published_count(self, local_date: str) -> int:
        """Counts how many live (non-dry-run) videos were published to Facebook on this date."""
        record = await self.get_or_create_daily(local_date)
        vids = json.loads(record.video_ids or "[]")
        return len([v for v in vids if not str(v).startswith("dry_run_")])

    async def get_rolling_24h_live_published_count(self, lookback_hours: int = 24) -> int:
        """
        Counts confirmed live (non-dry-run) publications across a persistent rolling lookback window.
        Uses persistent VideoJob.published_at timestamps.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        stmt = (
            select(func.count(VideoJob.id))
            .where(
                VideoJob.status == "published",
                VideoJob.facebook_video_id.is_not(None),
                not_(VideoJob.facebook_video_id.like("dry_run_%")),
                VideoJob.published_at >= cutoff
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def reserve_publication_slot(
        self,
        local_date: str,
        max_quota: int,
        job_id: str,
        timezone_name: str = "Asia/Dhaka",
        pilot_mode: bool = False,
        pilot_max_live_posts: int = 1,
        pilot_lookback_hours: int = 24,
        is_dry_run_configured: bool = True
    ) -> Tuple[bool, bool]:
        """
        Atomically reserves a publication quota slot across concurrent jobs and processes.
        Calculates:
        1. Confirmed published videos today + active in-flight uploading jobs for daily quota.
        2. Rolling 24-hour confirmed live publications + active in-flight live uploads.

        Returns:
            Tuple[can_publish, force_dry_run]:
            - can_publish (bool): True if quota was reserved, False if blocked by quota.
            - force_dry_run (bool): True if live pilot limit reached and slot should execute in dry-run mode.
        """
        record = await self.get_or_create_daily(local_date, timezone_name)

        # Count other jobs currently in 'uploading' state across the system
        active_uploads_stmt = select(func.count(VideoJob.id)).where(
            VideoJob.status == "uploading",
            VideoJob.id != job_id
        )
        active_uploads_res = await self.session.execute(active_uploads_stmt)
        active_uploads = active_uploads_res.scalar_one() or 0

        # Strict Atomic Invariant: confirmed publications + active uploading slots must be < max_quota
        if (record.published_count + active_uploads) >= max_quota:
            return False, False

        # Atomic Rolling 24-Hour Pilot Live Limit Check
        force_dry_run = False
        if not is_dry_run_configured and pilot_mode:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=pilot_lookback_hours)
            stmt_live = select(func.count(VideoJob.id)).where(
                VideoJob.status == "published",
                VideoJob.facebook_video_id.is_not(None),
                not_(VideoJob.facebook_video_id.like("dry_run_%")),
                VideoJob.published_at >= cutoff
            )
            res_live = await self.session.execute(stmt_live)
            live_rolling_count = res_live.scalar_one() or 0

            # If confirmed 24h live posts + active in-flight uploads >= pilot limit,
            # this worker cannot upload live. It is atomically forced into dry-run mode.
            if (live_rolling_count + active_uploads) >= pilot_max_live_posts:
                force_dry_run = True

        # Atomically transition THIS job to 'uploading' to hold the reservation
        stmt = (
            update(VideoJob)
            .where(
                VideoJob.id == job_id,
                VideoJob.status.in_(["ready", "completed", "retry_pending", "pending", "processing"])
            )
            .values(
                status="uploading",
                stage="uploading_to_facebook"
            )
        )
        res = await self.session.execute(stmt)
        if res.rowcount != 1:
            # Job not in ready/retryable state or already seized by concurrent worker
            return False, False

        await self.session.commit()
        return True, force_dry_run

    async def is_slot_fulfilled(self, local_date: str, slot: str) -> bool:
        record = await self.get_or_create_daily(local_date)
        slots = json.loads(record.slots_fulfilled or "[]")
        return slot in slots


