import os
import time
import json
import psutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import zoneinfo
from backend.app.config import settings
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.repository import JobRepository, VideoRepository, SceneRepository, DailyPublicationRepository
from backend.app.services.story_planner import StoryPlanner
from backend.app.services.image_generator import ImageGeneratorService
from backend.app.services.voice_generator import VoiceGenerator
from backend.app.services.subtitle_generator import SubtitleGenerator
from backend.app.services.music_library import MusicLibraryService
from backend.app.services.video_renderer import VideoRenderer
from backend.app.services.quality_validator import QualityValidator
from backend.app.services.facebook_publisher import facebook_publisher

logger = logging.getLogger("ai_harness.worker")

class VideoPipelineOrchestrator:
    def __init__(self):
        self.story_planner = StoryPlanner()
        self.image_generator = ImageGeneratorService()
        self.voice_generator = VoiceGenerator()
        self.subtitle_generator = SubtitleGenerator()
        self.music_service = MusicLibraryService()
        self.video_renderer = VideoRenderer()
        self.quality_validator = QualityValidator()

    async def execute_job(self, job_id: str) -> bool:
        start_time = time.time()
        timings = {}
        initial_process = psutil.Process()
        initial_mem = initial_process.memory_info().rss / (1024 * 1024)

        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            video_repo = VideoRepository(session)
            scene_repo = SceneRepository(session)

            job = await job_repo.get_job_by_id(job_id)
            if not job:
                logger.error(f"Job {job_id} not found in database")
                return False

            logger.info(f"Starting pipeline execution for Job {job_id}: '{job.prompt}'")
            job_work_dir = settings.TEMP_DIR / f"job_{job_id}"
            job_work_dir.mkdir(parents=True, exist_ok=True)

            try:
                # ----------------------------------------------------
                # STAGE 1: STORY PLANNING
                # ----------------------------------------------------
                t0 = time.time()
                await job_repo.update_job_status(job_id, status="processing", progress=5, stage="planning")

                script = await self.story_planner.generate_script(
                    prompt=job.prompt,
                    style=job.style,
                    target_duration=job.requested_duration
                )
                timings["story_planning_seconds"] = round(time.time() - t0, 2)
                logger.info(f"Story planned: '{script.title}' with {len(script.scenes)} scenes")

                # Persist scenes in database
                scenes_to_create = []
                for s in script.scenes:
                    scenes_to_create.append({
                        "job_id": job_id,
                        "sequence_number": s.sequence_number,
                        "narration_text": s.narration_text,
                        "visual_prompt": s.visual_prompt,
                        "visual_backend": settings.VISUAL_PROVIDER,
                        "duration": s.estimated_duration,
                        "status": "pending"
                    })
                db_scenes = await scene_repo.create_scenes(scenes_to_create)
                caption = f"{script.title}\n\n{script.synopsis}"
                hashtags = "#DevlanceAi #AI #EmergingTech #Business #Innovation #Technology #Shorts"
                await job_repo.update_job_status(
                    job_id,
                    status="processing",
                    progress=20,
                    stage="visuals",
                    caption=caption,
                    hashtags=hashtags
                )

                # ----------------------------------------------------
                # STAGE 2: VISUAL GENERATION
                # ----------------------------------------------------
                t0 = time.time()
                generated_images = []
                for idx, scene_item in enumerate(script.scenes):
                    img_path = job_work_dir / f"scene_{scene_item.sequence_number:02d}.jpg"
                    success, backend_used, msg = await self.image_generator.generate_scene_image(
                        prompt=scene_item.visual_prompt,
                        output_path=img_path,
                        style=job.style,
                        width=settings.DEFAULT_WIDTH,
                        height=settings.DEFAULT_HEIGHT,
                        scene_index=scene_item.sequence_number,
                        character_details=scene_item.character_continuity
                    )
                    generated_images.append(img_path)
                    
                    # Update scene in DB
                    db_scene_id = db_scenes[idx].id
                    await scene_repo.update_scene(db_scene_id, {
                        "visual_backend": backend_used,
                        "image_path": str(img_path)
                    })

                timings["visual_generation_seconds"] = round(time.time() - t0, 2)
                await job_repo.update_job_status(job_id, status="processing", progress=45, stage="narration")

                # ----------------------------------------------------
                # STAGE 3: NARRATION GENERATION (TTS)
                # ----------------------------------------------------
                t0 = time.time()
                audio_files = []
                timed_scenes_meta = []
                current_time_offset = 0.0

                for idx, scene_item in enumerate(script.scenes):
                    audio_path = job_work_dir / f"scene_{scene_item.sequence_number:02d}.wav"
                    if job.enable_narration:
                        success, audio_dur, msg = await self.voice_generator.generate_scene_narration(
                            text=scene_item.narration_text,
                            output_path=audio_path
                        )
                    else:
                        audio_dur = scene_item.estimated_duration
                        audio_path = None

                    # Add slight natural pause (0.2s)
                    final_scene_dur = max(3.0, audio_dur + 0.2)
                    audio_files.append(audio_path)

                    # Update scene record in DB
                    db_scene_id = db_scenes[idx].id
                    await scene_repo.update_scene(db_scene_id, {
                        "audio_path": str(audio_path) if audio_path else None,
                        "duration": round(final_scene_dur, 2),
                        "status": "generated"
                    })

                    timed_scenes_meta.append({
                        "sequence_number": scene_item.sequence_number,
                        "narration_text": scene_item.narration_text,
                        "start_time": current_time_offset,
                        "duration": final_scene_dur,
                        "image_path": generated_images[idx],
                        "audio_path": audio_path,
                        "motion_type": scene_item.motion_type
                    })
                    current_time_offset += final_scene_dur

                timings["tts_generation_seconds"] = round(time.time() - t0, 2)
                total_story_duration = current_time_offset
                await job_repo.update_job_status(job_id, status="processing", progress=65, stage="subtitles")

                # ----------------------------------------------------
                # STAGE 4: SUBTITLE GENERATION
                # ----------------------------------------------------
                t0 = time.time()
                ass_sub_path = job_work_dir / "subtitles.ass"
                srt_sub_path = job_work_dir / "subtitles.srt"
                
                self.subtitle_generator.generate_ass(
                    timed_scenes=timed_scenes_meta,
                    output_path=ass_sub_path,
                    width=settings.DEFAULT_WIDTH,
                    height=settings.DEFAULT_HEIGHT
                )
                self.subtitle_generator.generate_srt(
                    timed_scenes=timed_scenes_meta,
                    output_path=srt_sub_path
                )
                timings["subtitles_seconds"] = round(time.time() - t0, 2)
                await job_repo.update_job_status(job_id, status="processing", progress=75, stage="rendering")

                # ----------------------------------------------------
                # STAGE 5: VIDEO RENDERING
                # ----------------------------------------------------
                t0 = time.time()
                scene_clips = []
                for sc in timed_scenes_meta:
                    clip_path = job_work_dir / f"clip_{sc['sequence_number']:02d}.mp4"
                    success = await self.video_renderer.render_scene_clip(
                        image_path=sc["image_path"],
                        audio_path=sc["audio_path"],
                        output_clip_path=clip_path,
                        duration=sc["duration"],
                        motion_type=sc["motion_type"],
                        width=settings.DEFAULT_WIDTH,
                        height=settings.DEFAULT_HEIGHT
                    )
                    if not success:
                        raise RuntimeError(f"Failed to render clip for scene {sc['sequence_number']}")
                    scene_clips.append(clip_path)

                # Background music & Sound Effects (Whooshes, Risers, Sub-Bass Hits)
                bgm_path = None
                if job.enable_bgm:
                    bgm_path = job_work_dir / "bgm.wav"
                    self.music_service.get_background_track(job.style, total_story_duration, bgm_path)

                sfx_path = None
                if getattr(settings, "ENABLE_TRANSITION_SFX", True):
                    scene_times = [sc["start_time"] for sc in timed_scenes_meta]
                    sfx_path = self.music_service.generate_timeline_sfx(
                        scene_times, total_story_duration, job_work_dir / "sfx.wav"
                    )

                final_video_name = f"story_{job_id[:8]}_{int(time.time())}.mp4"
                final_output_path = settings.OUTPUT_DIR / final_video_name

                render_ok, render_msg = await self.video_renderer.assemble_final_video(
                    scene_clip_paths=scene_clips,
                    output_video_path=final_output_path,
                    subtitle_path=ass_sub_path if job.enable_subtitles else None,
                    bgm_path=bgm_path,
                    sfx_path=sfx_path,
                    enable_bgm=job.enable_bgm,
                    enable_subtitles=job.enable_subtitles,
                    bgm_volume=settings.BACKGROUND_MUSIC_VOLUME,
                    sfx_volume=getattr(settings, "SFX_VOLUME", 0.22)
                )
                if not render_ok:
                    raise RuntimeError(f"Video assembly failed: {render_msg}")

                timings["video_render_seconds"] = round(time.time() - t0, 2)
                await job_repo.update_job_status(job_id, status="processing", progress=90, stage="validating")

                # ----------------------------------------------------
                # STAGE 6: QUALITY VALIDATION & QA GATE
                # ----------------------------------------------------
                t0 = time.time()
                validation = self.quality_validator.validate_for_upload(
                    video_path=final_output_path,
                    title=script.title,
                    caption=caption
                )
                timings["quality_validation_seconds"] = round(time.time() - t0, 2)

                if not validation.is_valid:
                    raise RuntimeError(f"Validation failed: {validation.error_message}")

                # Record Video in DB
                video_record = await video_repo.create_video({
                    "job_id": job_id,
                    "title": script.title,
                    "file_path": str(final_output_path),
                    "thumbnail_path": validation.thumbnail_path,
                    "duration": validation.duration,
                    "width": validation.width,
                    "height": validation.height,
                    "fps": validation.fps,
                    "file_size": validation.file_size_bytes,
                    "sha256_hash": validation.sha256_hash
                })

                # Record Benchmark Metrics
                total_job_time = round(time.time() - start_time, 2)
                end_mem = initial_process.memory_info().rss / (1024 * 1024)
                
                # Estimated daily throughput = 86400 / total_job_time
                est_daily = round(86400.0 / max(1.0, total_job_time), 1)

                benchmark_metrics = {
                    "total_duration_seconds": total_job_time,
                    "timings": timings,
                    "memory_mb": {"start": round(initial_mem, 1), "end": round(end_mem, 1), "delta": round(end_mem - initial_mem, 1)},
                    "rendered_duration": validation.duration,
                    "file_size_mb": round(validation.file_size_bytes / (1024 * 1024), 2),
                    "estimated_daily_throughput": est_daily,
                    "cpu_cores": psutil.cpu_count(logical=True)
                }

                # Mark as 'ready' (ready for scheduled Facebook publishing slot)
                final_status = "ready" if settings.FACEBOOK_PUBLISHING_ENABLED else "completed"
                final_stage = "ready" if settings.FACEBOOK_PUBLISHING_ENABLED else "done"

                await job_repo.update_job_status(
                    job_id=job_id,
                    status=final_status,
                    progress=100,
                    stage=final_stage,
                    benchmark_data=json.dumps(benchmark_metrics)
                )

                logger.info(f"Job {job_id} successfully rendered and validated [{final_status}] in {total_job_time}s! Output: {final_output_path}")

                # Auto cleanup temporary scene clips if enabled
                if settings.AUTO_CLEANUP_TEMP_FILES:
                    try:
                        import shutil
                        shutil.rmtree(job_work_dir, ignore_errors=True)
                    except Exception:
                        pass

                return True

            except Exception as e:
                err_text = str(e)
                logger.error(f"Job {job_id} encountered fatal error: {err_text}", exc_info=True)
                await job_repo.update_job_status(
                    job_id=job_id,
                    status="failed",
                    progress=100,
                    stage="error",
                    error_message=err_text
                )
                return False

    async def publish_job(self, job_id: str, slot: Optional[str] = None) -> bool:
        """
        Executes pre-upload QA gate and publishes a ready/completed video to the Facebook Page.
        Guarantees idempotency: will not double-publish if video already published.
        Updates persistent daily counter upon confirmed Facebook publication.
        """
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            daily_repo = DailyPublicationRepository(session)

            job = await job_repo.get_job_by_id(job_id)
            if not job or not job.video:
                err = f"Cannot publish job {job_id}: job or video record not found"
                logger.error(err)
                if job:
                    await job_repo.update_job_status(job_id, status="failed", stage="error", upload_error=err)
                return False

            # Check idempotency: if already published, skip
            if job.status == "published" and job.facebook_video_id:
                logger.info(f"Job {job_id} already published (Facebook Video ID: {job.facebook_video_id})")
                return True

            video_path = Path(job.video.file_path)
            if not video_path.exists():
                err = f"Rendered video file missing from disk: {video_path}"
                logger.error(f"Cannot publish job {job_id}: {err}")
                await job_repo.update_job_status(job_id, status="failed", upload_error=err)
                return False

            # Pre-upload Quality Assurance Gate
            caption = job.caption or f"{job.video.title}\n\nAutomated AI Documentary Breakdown"
            qa_res = self.quality_validator.validate_for_upload(
                video_path=video_path,
                title=job.video.title,
                caption=caption
            )
            if not qa_res.is_valid:
                err = f"QA Gate Rejected: {qa_res.error_message}"
                logger.error(f"Job {job_id} failed pre-upload QA gate: {err}")
                await job_repo.update_job_status(job_id, status="failed", stage="qa_failed", upload_error=err)
                return False

            # Check atomic daily quota in database before initiating upload
            tz = zoneinfo.ZoneInfo(settings.TIMEZONE)
            local_now = datetime.now(tz)
            local_date_str = local_now.strftime("%Y-%m-%d")
            today_count = await daily_repo.get_today_count(local_date_str)
            if today_count >= settings.MAX_DAILY_PUBLISHED_VIDEOS:
                err = f"Daily publication quota ({today_count}/{settings.MAX_DAILY_PUBLISHED_VIDEOS}) reached for {local_date_str}."
                logger.warning(f"Aborting publication for Job {job_id}: {err}")
                return False

            # Mark state as uploading before calling API
            attempts = (job.upload_attempts or 0) + 1
            await job_repo.update_job_status(
                job_id,
                status="uploading",
                stage="uploading_to_facebook",
                upload_attempts=attempts
            )

            # Call Facebook Publisher
            hashtags = job.hashtags or "#DevlanceAi #AI #EmergingTech #Business #Innovation #Technology #Shorts"
            result = await facebook_publisher.publish_video(
                video_path=video_path,
                title=job.video.title,
                caption=caption,
                hashtags=hashtags,
                job_id=job_id
            )

            tz = zoneinfo.ZoneInfo(settings.TIMEZONE)
            local_now = datetime.now(tz)
            local_date_str = local_now.strftime("%Y-%m-%d")

            if result.success:
                slot_name = slot or local_now.strftime("%H:%M")
                await job_repo.update_job_status(
                    job_id,
                    status="published",
                    stage="published",
                    progress=100,
                    facebook_video_id=result.video_id,
                    facebook_post_id=result.post_id,
                    published_at=datetime.utcnow()
                )
                await daily_repo.record_publication(
                    local_date=local_date_str,
                    slot=slot_name,
                    video_id=result.video_id or job_id,
                    timezone=settings.TIMEZONE
                )
                logger.info(f"Successfully published Job {job_id} to Facebook Page (Video ID: {result.video_id}) for slot {slot_name}")
                return True
            else:
                logger.warning(f"Failed to publish Job {job_id} to Facebook: {result.error_message}")
                new_status = "retry_pending" if (result.retryable and attempts < 2) else "failed"
                await job_repo.update_job_status(
                    job_id,
                    status=new_status,
                    stage="upload_error",
                    upload_error=result.error_message
                )
                return False

class WorkerService:
    def __init__(self):
        self.orchestrator = VideoPipelineOrchestrator()
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self.running = True
        logger.info("Background Worker Service starting...")
        
        # Recover interrupted jobs
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            recovered = await job_repo.recover_stale_jobs()
            if recovered > 0:
                logger.warning(f"Recovered {recovered} interrupted job(s) from previous server crash/restart.")

        self._task = asyncio.create_task(self._worker_loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background Worker Service stopped.")

    async def _worker_loop(self):
        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    job_repo = JobRepository(session)
                    running_count = await job_repo.get_running_jobs_count()
                    
                    if running_count < settings.MAX_CONCURRENT_JOBS:
                        pending_job = await job_repo.get_next_pending_job()
                        if pending_job:
                            job_id = pending_job.id
                            await job_repo.update_job_status(job_id, status="processing", progress=2, stage="initializing")
                            # Process job in background
                            asyncio.create_task(self.orchestrator.execute_job(job_id))
            except Exception as e:
                logger.error(f"Worker loop exception: {e}")

            await asyncio.sleep(2.0)

worker_service = WorkerService()
