import pytest
import shutil
from pathlib import Path
from backend.app.config import settings
from backend.app.services.image_generator import StoryboardCanvasProvider
from backend.app.services.video_renderer import VideoRenderer
from backend.app.services.quality_validator import QualityValidator

@pytest.mark.asyncio
async def test_image_and_video_render_pipeline(tmp_path):
    # Only run video render test if ffmpeg is available
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not installed in test environment")

    # 1. Generate image
    img_provider = StoryboardCanvasProvider()
    img_path = tmp_path / "test_scene.jpg"
    ok, backend_name, msg = await img_provider.generate_image(
        prompt="Anime night sky over Tokyo",
        output_path=img_path,
        style="anime",
        width=360,
        height=640,
        scene_index=1
    )
    assert ok is True
    assert img_path.exists()
    assert img_path.stat().st_size > 1000

    # 2. Render short clip (2 seconds)
    renderer = VideoRenderer()
    renderer.fps = 15  # Fast test fps
    clip_path = tmp_path / "test_clip.mp4"
    render_ok = await renderer.render_scene_clip(
        image_path=img_path,
        audio_path=None,
        output_clip_path=clip_path,
        duration=2.0,
        motion_type="zoom_in",
        width=360,
        height=640
    )
    assert render_ok is True
    assert clip_path.exists()

    # 3. Validate clip with FFprobe
    validator = QualityValidator()
    val = validator.validate_video(
        video_path=clip_path,
        expected_duration=2.0,
        expected_width=360,
        expected_height=640
    )
    assert val.is_valid is True
    assert val.width == 360
    assert val.height == 640
    assert val.duration >= 1.5
    assert val.has_audio is True
