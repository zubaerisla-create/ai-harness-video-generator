from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.database import VideoJob, Video, Scene, User

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
        benchmark_data: Optional[str] = None
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
        if status == "processing":
            values["started_at"] = datetime.utcnow()
        elif status in ["completed", "failed", "cancelled"]:
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
        stmt = select(func.count(VideoJob.id)).where(VideoJob.status == "processing")
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def recover_stale_jobs(self) -> int:
        # Marks any 'processing' jobs as 'failed' (interrupted by server restart)
        stmt = (
            update(VideoJob)
            .where(VideoJob.status == "processing")
            .values(
                status="failed",
                error_message="Job interrupted due to server/worker restart. Can be retried.",
                completed_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

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
