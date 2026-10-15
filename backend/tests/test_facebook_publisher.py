import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.config import settings
from backend.app.services.facebook_publisher import (
    FacebookPublisherService,
    mask_token,
    PublishResult
)
from backend.app.services.quality_validator import QualityValidator
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.repository import DailyPublicationRepository

def test_mask_token():
    assert mask_token(None) == "<EMPTY_TOKEN>"
    assert mask_token("") == "<EMPTY_TOKEN>"
    assert mask_token("short") == "***"
    token = "EAArHHOkQ118BStmDmGYZCeXdJFFRLdKEAxUHnn8jVESqfgM948oznrf0yCZBrtZBVk0je66"
    masked = mask_token(token)
    assert masked.startswith("EAArH...")
    assert masked.endswith("je66")
    assert "BStmDmGYZ" not in masked

@pytest.mark.asyncio
async def test_facebook_publisher_dry_run(tmp_path: Path):
    # Create dummy video file
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"dummy video data content that is sufficiently large" * 500)

    publisher = FacebookPublisherService(page_id="123456", access_token="test_token")
    
    with patch("backend.app.config.settings.DRY_RUN", True):
        res = await publisher.publish_video(
            video_path=video_file,
            title="AI Revolution in 2026",
            caption="Exploring autonomous swarms",
            hashtags="#AI #Tech"
        )
        assert res.success is True
        assert res.is_dry_run is True
        assert res.video_id is not None
        assert res.video_id.startswith("dry_run_")

@pytest.mark.asyncio
async def test_facebook_publisher_missing_credentials(tmp_path: Path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"dummy content" * 1000)

    publisher = FacebookPublisherService(page_id="", access_token="")
    with patch("backend.app.config.settings.DRY_RUN", False):
        res = await publisher.publish_video(
            video_path=video_file,
            title="No credentials test",
            caption="test caption"
        )
        assert res.success is False
        assert "Missing Facebook credentials" in res.error_message

@pytest.mark.asyncio
async def test_facebook_publisher_mocked_success(tmp_path: Path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"0" * 20000)

    publisher = FacebookPublisherService(page_id="1120237794506468", access_token="EAArMockToken123456")
    
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"id": "fb_video_999888777", "post_id": "fb_post_111222333"}
    mock_post_resp.headers = {"content-type": "application/json"}

    with patch("backend.app.config.settings.DRY_RUN", False), \
         patch("backend.app.config.settings.FACEBOOK_PUBLISHING_ENABLED", True):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_post_resp):
            with patch.object(publisher, "verify_video_status", new_callable=AsyncMock, return_value={"published": True}):
                res = await publisher.publish_video(
                    video_path=video_file,
                    title="Breakthrough in Quantum Computing",
                    caption="Scientists achieve room-temperature quantum states.",
                    hashtags="#Quantum #AI"
                )
                assert res.success is True
                assert res.video_id == "fb_video_999888777"
                assert res.post_id == "fb_post_111222333"

@pytest.mark.asyncio
async def test_daily_publication_repository():
    import uuid
    async with AsyncSessionLocal() as session:
        repo = DailyPublicationRepository(session)
        test_date = f"2099-01-{uuid.uuid4().hex[:6]}"  # Unique synthetic test date
        
        # Initial count should be 0
        cnt0 = await repo.get_today_count(test_date)
        assert cnt0 == 0

        # Record slot 1 publication
        rec1 = await repo.record_publication(
            local_date=test_date,
            slot="09:00",
            video_id="video_item_1"
        )
        assert rec1.published_count == 1
        assert await repo.is_slot_fulfilled(test_date, "09:00") is True
        assert await repo.is_slot_fulfilled(test_date, "12:00") is False

        # Record slot 2 publication
        rec2 = await repo.record_publication(
            local_date=test_date,
            slot="12:00",
            video_id="video_item_2"
        )
        assert rec2.published_count == 2
        assert await repo.is_slot_fulfilled(test_date, "12:00") is True

@pytest.mark.asyncio
async def test_quality_validator_pre_upload_gate(tmp_path: Path):
    validator = QualityValidator()
    
    # Missing file
    res = validator.validate_for_upload(tmp_path / "nonexistent.mp4", "Title", "Caption")
    assert res.is_valid is False
    assert "does not exist" in res.error_message

    # Empty title
    empty_video = tmp_path / "test.mp4"
    empty_video.write_bytes(b"empty")
    res2 = validator.validate_for_upload(empty_video, "", "Caption")
    assert res2.is_valid is False
    assert "title is missing" in res2.error_message
