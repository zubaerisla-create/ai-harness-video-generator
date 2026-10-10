import pytest
from backend.app.services.story_planner import StoryPlanner

@pytest.mark.asyncio
async def test_story_planner_fallback_generation():
    planner = StoryPlanner()
    # Force fallback by passing custom inputs
    script = planner._generate_fallback_script(
        prompt="A young student discovers coding",
        style="anime",
        num_scenes=8,
        target_duration=120,
        style_enhancer="vibrant Japanese anime aesthetic"
    )
    assert script.title is not None
    assert len(script.scenes) == 8
    assert "Protagonist" in script.characters
    
    # Check that each scene has a visual directive, duration, and motion type
    for scene in script.scenes:
        assert scene.visual_prompt and len(scene.visual_prompt) > 10
        assert scene.estimated_duration > 0
        assert scene.motion_type in ["zoom_in", "zoom_out", "pan_left", "pan_right", "slow_push"]
