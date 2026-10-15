import pytest
from pathlib import Path
from backend.app.services.online_researcher import online_researcher
from backend.app.services.story_planner import StoryPlanner
from backend.app.services.image_generator import ImageGeneratorService

@pytest.mark.asyncio
async def test_online_researcher_topic_facts():
    # Test researching a real tech topic
    topic = "Nvidia Blackwell GPU AI chips"
    result = await online_researcher.research_topic(topic, style="ai_news")
    assert result is not None
    assert "topic" in result
    assert "headline_facts" in result
    assert "context_summary" in result
    assert len(result["context_summary"]) > 20

@pytest.mark.asyncio
async def test_online_researcher_trending_topics():
    # Test fetching live trending stories
    trending = await online_researcher.get_trending_topics("business_strategy", limit=3)
    assert isinstance(trending, list)
    if trending:
        title, desc, meta = trending[0]
        assert len(title) > 5
        assert "headline" in meta

@pytest.mark.asyncio
async def test_script_uniqueness_across_topics():
    # Verify two different topics generate completely distinct narratives
    planner = StoryPlanner()
    script1 = await planner.generate_script("Apple Vision Pro production scale", style="emerging_tech", target_duration=30)
    script2 = await planner.generate_script("Costco Wholesale profit margin model", style="business_strategy", target_duration=30)

    assert script1.title != script2.title
    assert len(script1.scenes) >= 3
    assert len(script2.scenes) >= 3

    # Check that the narration texts are completely different
    narr1 = " ".join([s.narration_text for s in script1.scenes])
    narr2 = " ".join([s.narration_text for s in script2.scenes])
    assert narr1 != narr2
    assert "Apple" in narr1 or "Vision" in narr1 or "Production" in narr1
    assert "Costco" in narr2 or "Margin" in narr2 or "Wholesale" in narr2

@pytest.mark.asyncio
async def test_realistic_image_generation(tmp_path):
    service = ImageGeneratorService()
    img_path = tmp_path / "real_photo_test.jpg"

    # Test generating realistic photo for a real entity
    success, backend, msg = await service.generate_scene_image(
        prompt="Costco Wholesale warehouse building and store exterior",
        output_path=img_path,
        style="business_strategy",
        width=360,
        height=640,
        scene_index=1,
        character_details="Costco"
    )
    assert success is True
    assert img_path.exists()
    assert img_path.stat().st_size > 1000
