import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from backend.app.config import settings
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.repository import JobRepository, DailyPublicationRepository, VideoRepository
from backend.app.services.facebook_publisher import FacebookPublisherService, PublishResult
from backend.app.workers.queue import VideoPipelineOrchestrator

@pytest.mark.asyncio
async def test_daily_quota_enforcement():
    """Verify that reaching the 5-video quota strictly blocks further publications."""
    async with AsyncSessionLocal() as session:
        daily_repo = DailyPublicationRepository(session)
        test_date = f"2099-12-quota-test"
        
        # Seed 5 publications for test date
        for i in range(1, 6):
            await daily_repo.record_publication(
                local_date=test_date,
                slot=f"slot_{i}",
                video_id=f"test_vid_{i}",
                timezone="Asia/Dhaka"
            )
            
        cnt = await daily_repo.get_today_count(test_date)
        assert cnt == 5
        
        daily_rec = await daily_repo.get_or_create_daily(test_date, "Asia/Dhaka")
        assert daily_rec.published_count >= settings.MAX_DAILY_PUBLISHED_VIDEOS

@pytest.mark.asyncio
async def test_failed_upload_does_not_increment_quota(tmp_path: Path):
    """Verify that failed upload attempts never increment the daily publication counter."""
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        daily_repo = DailyPublicationRepository(session)
        
        test_date = f"2099-12-fail-test"
        initial_cnt = await daily_repo.get_today_count(test_date)
        
        # Create a mock job
        job = await job_repo.create_job({"prompt": "Test failure quota safety"})
        video_file = tmp_path / "test_vid.mp4"
        video_file.write_bytes(b"0" * 20000)
        
        from backend.app.database.repository import VideoRepository
        v_repo = VideoRepository(session)
        vid = await v_repo.create_video({
            "job_id": job.id,
            "title": "Failed Upload Title",
            "file_path": str(video_file),
            "duration": 45.0,
            "width": 720,
            "height": 1280
        })
        
        orchestrator = VideoPipelineOrchestrator()
        
        # Mock publisher returning failure
        with patch.object(
            orchestrator.quality_validator,
            "validate_for_upload",
            return_value=MagicMock(is_valid=True)
        ):
            with patch(
                "backend.app.workers.queue.facebook_publisher.publish_video",
                new_callable=AsyncMock,
                return_value=PublishResult(
                    success=False,
                    error_message="Simulated Meta API 500 Network Timeout",
                    retryable=True
                )
            ):
                success = await orchestrator.publish_job(job.id)
                assert success is False
                
        # Counter must NOT have incremented
        final_cnt = await daily_repo.get_today_count(test_date)
        assert final_cnt == initial_cnt
        
    # Query in fresh session to bypass identity map cache
    async with AsyncSessionLocal() as verify_session:
        verify_repo = JobRepository(verify_session)
        updated_job = await verify_repo.get_job_by_id(job.id)
        assert updated_job.status == "retry_pending"
        assert updated_job.upload_attempts == 1
        assert "Simulated Meta API" in updated_job.upload_error

@pytest.mark.asyncio
async def test_restart_recovery_of_interrupted_jobs():
    """Verify that server crash recovery restores stuck 'uploading' and 'processing' jobs without duplicates."""
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        
        # 1. Job stuck in 'uploading' when server restarted
        job_up = await job_repo.create_job({"prompt": "Job stuck uploading"})
        await job_repo.update_job_status(job_up.id, status="uploading", stage="uploading_to_facebook")
        
        # 2. Job stuck in 'processing' when server restarted
        job_proc = await job_repo.create_job({"prompt": "Job stuck processing"})
        await job_repo.update_job_status(job_proc.id, status="processing", stage="rendering")
        
        # Run crash recovery
        recovered_count = await job_repo.recover_stale_jobs()
        assert recovered_count >= 2
        
        rec_up = await job_repo.get_job_by_id(job_up.id)
        assert rec_up.status == "retry_pending"
        assert "Upload interrupted by server restart" in rec_up.upload_error
        
        rec_proc = await job_repo.get_job_by_id(job_proc.id)
        assert rec_proc.status == "failed"
        assert "interrupted due to server/worker restart" in rec_proc.error_message

@pytest.mark.asyncio
async def test_recent_publication_interval_guard():
    """Verify that FacebookPublisherService blocks publishing if last video was published < 120m ago."""
    publisher = FacebookPublisherService(page_id="1120237794506468", access_token="test_token")
    
    # 1. Case A: Recent video published 30 mins ago -> Should BLOCK
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    mock_resp_recent = MagicMock()
    mock_resp_recent.status_code = 200
    mock_resp_recent.json.return_value = {
        "data": [{"id": "fb_recent_123", "created_time": recent_time, "published": True}]
    }
    
    with patch("backend.app.config.settings.DRY_RUN", False):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_recent):
            can_pub, reason, _ = await publisher.check_recent_publications_on_facebook(min_interval_minutes=120)
            assert can_pub is False
            assert "Enforcing interval guard" in reason
            assert "fb_recent_123" in reason
            
    # 2. Case B: Recent video published 150 mins ago -> Should ALLOW
    older_time = (datetime.now(timezone.utc) - timedelta(minutes=150)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    mock_resp_older = MagicMock()
    mock_resp_older.status_code = 200
    mock_resp_older.json.return_value = {
        "data": [{"id": "fb_older_456", "created_time": older_time, "published": True}]
    }
    
    with patch("backend.app.config.settings.DRY_RUN", False):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_older):
            can_pub, reason, _ = await publisher.check_recent_publications_on_facebook(min_interval_minutes=120)
            assert can_pub is True
            assert reason is None

@pytest.mark.asyncio
async def test_reconcile_video_with_facebook():
    """Verify that ambiguous timeouts reconcile existing uploads matching title/caption rather than duplicating."""
    publisher = FacebookPublisherService(page_id="1120237794506468", access_token="test_token")
    
    mock_videos = {
        "data": [
            {
                "id": "fb_reconciled_999",
                "title": "Autonomous AI Agents in Business",
                "description": "How autonomous AI agents are changing corporate strategy in 2026.\n\n#AI",
                "created_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000"),
                "published": True
            }
        ]
    }
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_videos
    
    with patch("backend.app.config.settings.DRY_RUN", False):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            matched = await publisher.reconcile_video_with_facebook(
                title="Autonomous AI Agents in Business",
                caption="How autonomous AI agents are changing corporate strategy"
            )
            assert matched is not None
            assert matched.get("id") == "fb_reconciled_999"

@pytest.mark.asyncio
async def test_publish_job_blocks_when_daily_quota_full(tmp_path: Path):
    """Verify that publish_job aborts before attempting upload when daily quota is full."""
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        
        # Create a mock video job
        job = await job_repo.create_job({"prompt": "Testing atomic quota block"})
        video_file = tmp_path / "vid_quota.mp4"
        video_file.write_bytes(b"0" * 20000)
        
        from backend.app.database.repository import VideoRepository
        v_repo = VideoRepository(session)
        await v_repo.create_video({
            "job_id": job.id,
            "title": "Blocked by Quota",
            "file_path": str(video_file),
            "duration": 45.0,
            "width": 720,
            "height": 1280
        })
        
        orchestrator = VideoPipelineOrchestrator()
        with patch.object(
            orchestrator.quality_validator,
            "validate_for_upload",
            return_value=MagicMock(is_valid=True)
        ):
            with patch.object(
                DailyPublicationRepository,
                "reserve_publication_slot",
                new_callable=AsyncMock,
                return_value=False
            ):
                # Attempt to publish -> should be blocked by quota before hitting publisher
                success = await orchestrator.publish_job(job.id)
                assert success is False

@pytest.mark.asyncio
async def test_atomic_quota_reservation_concurrency(tmp_path: Path):
    """Verify that reserve_publication_slot accounts for in-flight uploading jobs atomically."""
    import uuid
    async with AsyncSessionLocal() as session:
        daily_repo = DailyPublicationRepository(session)
        job_repo = JobRepository(session)
        test_date = f"2099-07-{uuid.uuid4().hex[:6]}"

        # Create two jobs in ready state
        job1 = await job_repo.create_job({"prompt": "Job 1"})
        await job_repo.update_job_status(job1.id, status="ready")
        
        job2 = await job_repo.create_job({"prompt": "Job 2"})
        await job_repo.update_job_status(job2.id, status="ready")

        # Set max_quota to 1
        # Job 1 reserves the single slot
        res1 = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job1.id)
        assert res1 is True
        
        # Verify job1 is now 'uploading'
        refreshed_job1 = await job_repo.get_job_by_id(job1.id)
        assert refreshed_job1.status == "uploading"

        # Job 2 attempts to reserve while job1 is in-flight -> MUST fail atomically
        res2 = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job2.id)
        assert res2 is False

        # If job 1 fails and status becomes 'failed', reservation is released
        await job_repo.update_job_status(job1.id, status="failed")
        res2_retry = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job2.id)
        assert res2_retry is True
        await job_repo.update_job_status(job2.id, status="failed")

@pytest.mark.asyncio
async def test_pilot_rollout_mode_dry_run_fallback(tmp_path: Path):
    """Verify that under PILOT_ONE_POST_ROLLOUT, once 1 live post exists, subsequent slots run in dry-run mode."""
    import uuid
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        v_repo = VideoRepository(session)
        daily_repo = DailyPublicationRepository(session)

        job = await job_repo.create_job({"prompt": "Pilot rollout test"})
        await job_repo.update_job_status(job.id, status="ready")
        video_file = tmp_path / "vid_pilot.mp4"
        video_file.write_bytes(b"0" * 20000)

        await v_repo.create_video({
            "job_id": job.id,
            "title": "Pilot Rollout Video",
            "file_path": str(video_file),
            "duration": 45.0,
            "width": 720,
            "height": 1280
        })

        orchestrator = VideoPipelineOrchestrator()
        with patch("backend.app.config.settings.DRY_RUN", False), \
             patch("backend.app.config.settings.PILOT_ONE_POST_ROLLOUT", True), \
             patch.object(orchestrator.quality_validator, "validate_for_upload", return_value=MagicMock(is_valid=True)), \
             patch.object(DailyPublicationRepository, "get_live_published_count", new_callable=AsyncMock, return_value=1), \
             patch.object(DailyPublicationRepository, "reserve_publication_slot", new_callable=AsyncMock, return_value=True), \
             patch.object(DailyPublicationRepository, "record_publication", new_callable=AsyncMock):
            with patch("backend.app.services.facebook_publisher.facebook_publisher.publish_video", new_callable=AsyncMock) as mock_pub:
                mock_pub.return_value = MagicMock(success=True, video_id="dry_run_sim_123", post_id="dry_run_post_123")
                success = await orchestrator.publish_job(job.id, slot="12:00")
                assert success is True
                # Assert that dry_run_override was passed as True!
                mock_pub.assert_called_once()
                _, kwargs = mock_pub.call_args
                assert kwargs.get("dry_run_override") is True

@pytest.mark.asyncio
async def test_emergency_kill_switch_api():
    """Verify that calling /api/facebook/emergency-kill-switch immediately halts live publishing."""
    from httpx import AsyncClient, ASGITransport
    from backend.app.main import app
    from backend.app.config import settings

    settings.FACEBOOK_PUBLISHING_ENABLED = True
    settings.DRY_RUN = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/facebook/emergency-kill-switch")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "killed"
        assert data["facebook_publishing_enabled"] is False
        assert data["dry_run"] is True

        # Confirm global settings were immediately modified
        assert settings.FACEBOOK_PUBLISHING_ENABLED is False
        assert settings.DRY_RUN is True


