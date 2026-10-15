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
                return_value=(False, False)
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
        can_pub1, _ = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job1.id)
        assert can_pub1 is True
        
        # Verify job1 is now 'uploading'
        refreshed_job1 = await job_repo.get_job_by_id(job1.id)
        assert refreshed_job1.status == "uploading"

        # Job 2 attempts to reserve while job1 is in-flight -> MUST fail atomically
        can_pub2, _ = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job2.id)
        assert can_pub2 is False

        # If job 1 fails and status becomes 'failed', reservation is released
        await job_repo.update_job_status(job1.id, status="failed")
        can_pub2_retry, _ = await daily_repo.reserve_publication_slot(test_date, max_quota=1, job_id=job2.id)
        assert can_pub2_retry is True
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
             patch.object(DailyPublicationRepository, "get_rolling_24h_live_published_count", new_callable=AsyncMock, return_value=1), \
             patch.object(DailyPublicationRepository, "reserve_publication_slot", new_callable=AsyncMock, return_value=(True, True)), \
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

@pytest.mark.asyncio
async def test_midnight_rollover_rolling_24h_guard(tmp_path: Path):
    """
    Verify that a live post published before midnight (e.g. 12 hours ago)
    still enforces force_dry_run=True after midnight rollover on the new calendar day.
    Also verifies that after 24 hours have elapsed, live publishing is allowed again.
    """
    import uuid
    from backend.app.models.database import VideoJob
    from sqlalchemy import update

    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        daily_repo = DailyPublicationRepository(session)

        # Baseline count before test
        initial_live = await daily_repo.get_rolling_24h_live_published_count(lookback_hours=24)
        target_pilot_max = initial_live + 1

        # 1. Simulate a live post published 12 hours ago (yesterday night)
        past_job = await job_repo.create_job({"prompt": "Yesterday night live post"})
        past_published_at = datetime.now(timezone.utc) - timedelta(hours=12)
        await job_repo.update_job_status(
            past_job.id,
            status="published",
            stage="published",
            facebook_video_id=f"fb_live_yesterday_{uuid.uuid4().hex[:6]}"
        )
        # Directly set published_at on the job to 12h ago
        await session.execute(
            update(VideoJob)
            .where(VideoJob.id == past_job.id)
            .values(published_at=past_published_at)
        )
        await session.commit()

        # Confirm rolling 24h count sees this publication
        rolling_count = await daily_repo.get_rolling_24h_live_published_count(lookback_hours=24)
        assert rolling_count == initial_live + 1

        # 2. Today is a new calendar date (e.g. "2099-01-02") with zero posts recorded today
        new_date_str = f"2099-01-{uuid.uuid4().hex[:4]}"
        new_job = await job_repo.create_job({"prompt": "New morning post after midnight"})
        await job_repo.update_job_status(new_job.id, status="ready")

        can_pub, force_dry_run = await daily_repo.reserve_publication_slot(
            local_date=new_date_str,
            max_quota=10,
            job_id=new_job.id,
            pilot_mode=True,
            pilot_max_live_posts=target_pilot_max,
            pilot_lookback_hours=24,
            is_dry_run_configured=False
        )

        # MUST allow publication to proceed (daily quota has capacity), BUT MUST FORCE DRY RUN!
        assert can_pub is True
        assert force_dry_run is True

        # Clean up new_job
        await job_repo.update_job_status(new_job.id, status="failed")

        # 3. Now shift the past job to 25 hours ago (outside rolling window)
        old_published_at = datetime.now(timezone.utc) - timedelta(hours=25)
        await session.execute(
            update(VideoJob)
            .where(VideoJob.id == past_job.id)
            .values(published_at=old_published_at)
        )
        await session.commit()

        # Job 3 attempts to reserve after rolling window expired
        job3 = await job_repo.create_job({"prompt": "Post after 24h window passed"})
        await job_repo.update_job_status(job3.id, status="ready")

        can_pub3, force_dry_run3 = await daily_repo.reserve_publication_slot(
            local_date=new_date_str,
            max_quota=10,
            job_id=job3.id,
            pilot_mode=True,
            pilot_max_live_posts=target_pilot_max,
            pilot_lookback_hours=24,
            is_dry_run_configured=False
        )
        assert can_pub3 is True
        assert force_dry_run3 is False  # Now live publishing is allowed!
        await job_repo.update_job_status(job3.id, status="failed")
        await job_repo.update_job_status(past_job.id, status="failed")

@pytest.mark.asyncio
async def test_concurrent_pilot_reservation_race_condition():
    """
    Verify that concurrent worker tasks trying to reserve the single pilot live slot
    cannot race: exactly one worker gets live permission (force_dry_run=False),
    while concurrent workers are atomically forced into dry-run (force_dry_run=True).
    """
    import uuid
    async with AsyncSessionLocal() as session:
        daily_repo = DailyPublicationRepository(session)
        job_repo = JobRepository(session)
        test_date = f"2099-08-{uuid.uuid4().hex[:6]}"

        initial_live = await daily_repo.get_rolling_24h_live_published_count(lookback_hours=24)
        target_pilot_max = initial_live + 1

        job_a = await job_repo.create_job({"prompt": "Concurrent Job A"})
        await job_repo.update_job_status(job_a.id, status="ready")

        job_b = await job_repo.create_job({"prompt": "Concurrent Job B"})
        await job_repo.update_job_status(job_b.id, status="ready")

        # Worker A reserves first
        can_pub_a, force_dry_a = await daily_repo.reserve_publication_slot(
            local_date=test_date,
            max_quota=10,
            job_id=job_a.id,
            pilot_mode=True,
            pilot_max_live_posts=target_pilot_max,
            pilot_lookback_hours=24,
            is_dry_run_configured=False
        )
        assert can_pub_a is True
        assert force_dry_a is False  # Worker A gets the live slot

        # Worker B reserves concurrently while Job A is in 'uploading' state
        can_pub_b, force_dry_b = await daily_repo.reserve_publication_slot(
            local_date=test_date,
            max_quota=10,
            job_id=job_b.id,
            pilot_mode=True,
            pilot_max_live_posts=target_pilot_max,
            pilot_lookback_hours=24,
            is_dry_run_configured=False
        )
        assert can_pub_b is True
        assert force_dry_b is True  # Worker B is atomically locked to dry-run!

        # Cleanup
        await job_repo.update_job_status(job_a.id, status="failed")
        await job_repo.update_job_status(job_b.id, status="failed")

@pytest.mark.asyncio
async def test_restart_recovery_clears_active_upload_reservation():
    """
    Verify that server restart recovery transitions stuck 'uploading' jobs to 'retry_pending',
    thereby safely clearing active in-flight locks so subsequent slots are not blocked.
    """
    import uuid
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        daily_repo = DailyPublicationRepository(session)
        test_date = f"2099-09-{uuid.uuid4().hex[:6]}"

        # Stale job stuck in uploading
        job_stuck = await job_repo.create_job({"prompt": "Stuck before crash"})
        await job_repo.update_job_status(job_stuck.id, status="uploading", stage="uploading_to_facebook")

        # Before recovery: a new job with quota=1 is blocked by the active upload
        job_new = await job_repo.create_job({"prompt": "New job after reboot"})
        await job_repo.update_job_status(job_new.id, status="ready")

        can_pub_blocked, _ = await daily_repo.reserve_publication_slot(
            local_date=test_date,
            max_quota=1,
            job_id=job_new.id
        )
        assert can_pub_blocked is False

        # Run crash recovery
        recovered = await job_repo.recover_stale_jobs()
        assert recovered >= 1

        rec_job = await job_repo.get_job_by_id(job_stuck.id)
        assert rec_job.status == "retry_pending"

        # Now job_new can successfully reserve the slot
        can_pub_ok, _ = await daily_repo.reserve_publication_slot(
            local_date=test_date,
            max_quota=1,
            job_id=job_new.id
        )
        assert can_pub_ok is True

        await job_repo.update_job_status(job_new.id, status="failed")
        await job_repo.update_job_status(job_stuck.id, status="failed")

@pytest.mark.asyncio
async def test_failed_upload_releases_slot_and_preserves_pilot_limit(tmp_path: Path):
    """
    Verify that when an upload genuinely fails, the in-flight lock is released,
    rolling 24h live count is not incremented, and subsequent retries can proceed.
    """
    import uuid
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        v_repo = VideoRepository(session)
        daily_repo = DailyPublicationRepository(session)
        test_date = f"2099-10-{uuid.uuid4().hex[:6]}"

        initial_rolling = await daily_repo.get_rolling_24h_live_published_count(24)

        job = await job_repo.create_job({"prompt": "Failing upload job"})
        await job_repo.update_job_status(job.id, status="ready")
        video_file = tmp_path / "fail_vid.mp4"
        video_file.write_bytes(b"0" * 20000)
        await v_repo.create_video({
            "job_id": job.id,
            "title": "Failed Job Title",
            "file_path": str(video_file),
            "duration": 45.0,
            "width": 720,
            "height": 1280
        })

        orchestrator = VideoPipelineOrchestrator()
        with patch.object(orchestrator.quality_validator, "validate_for_upload", return_value=MagicMock(is_valid=True)), \
             patch("backend.app.workers.queue.facebook_publisher.publish_video", new_callable=AsyncMock) as mock_pub, \
             patch("backend.app.workers.queue.facebook_publisher.reconcile_video_with_facebook", new_callable=AsyncMock, return_value=None):
            mock_pub.return_value = PublishResult(
                success=False,
                error_message="Meta API Unrecoverable Error 400",
                retryable=False
            )
            success = await orchestrator.publish_job(job.id)
            assert success is False

        # In a fresh session, verify job status and counts
        async with AsyncSessionLocal() as verify_session:
            v_job_repo = JobRepository(verify_session)
            v_daily_repo = DailyPublicationRepository(verify_session)
            refreshed = await v_job_repo.get_job_by_id(job.id)
            assert refreshed.status == "failed"
            assert refreshed.facebook_video_id is None
            
            # Rolling count did not increase
            new_rolling = await v_daily_repo.get_rolling_24h_live_published_count(24)
            assert new_rolling == initial_rolling

@pytest.mark.asyncio
async def test_uncertain_upload_timeout_immediate_meta_reconciliation(tmp_path: Path):
    """
    Verify that when an upload encounters an ambiguous network timeout or retryable 5xx,
    orchestrator immediately calls reconcile_video_with_facebook(). If Meta confirms publication,
    the job is marked published with the reconciled ID, preventing duplicate uploads.
    """
    import uuid
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        v_repo = VideoRepository(session)
        daily_repo = DailyPublicationRepository(session)

        job = await job_repo.create_job({"prompt": "Ambiguous timeout job"})
        await job_repo.update_job_status(job.id, status="ready")
        video_file = tmp_path / "timeout_vid.mp4"
        video_file.write_bytes(b"0" * 20000)
        await v_repo.create_video({
            "job_id": job.id,
            "title": "Uncertain Timeout Video",
            "file_path": str(video_file),
            "duration": 45.0,
            "width": 720,
            "height": 1280
        })

        orchestrator = VideoPipelineOrchestrator()
        with patch.object(orchestrator.quality_validator, "validate_for_upload", return_value=MagicMock(is_valid=True)), \
             patch("backend.app.workers.queue.facebook_publisher.publish_video", new_callable=AsyncMock) as mock_pub, \
             patch("backend.app.workers.queue.facebook_publisher.reconcile_video_with_facebook", new_callable=AsyncMock) as mock_recon:
            
            # Simulated timeout error from Meta
            mock_pub.return_value = PublishResult(
                success=False,
                error_message="Meta Graph API call timed out after 180s",
                retryable=True
            )
            # Reconcile finds the video already processed on Meta!
            mock_recon.return_value = {"id": "fb_meta_reconciled_555", "title": "Uncertain Timeout Video"}

            success = await orchestrator.publish_job(job.id, slot="18:00")
            assert success is True
            mock_recon.assert_called_once()

        # Verify job marked published with the reconciled video ID
        async with AsyncSessionLocal() as verify_session:
            v_job_repo = JobRepository(verify_session)
            refreshed = await v_job_repo.get_job_by_id(job.id)
            assert refreshed.status == "published"
            assert refreshed.facebook_video_id == "fb_meta_reconciled_555"


