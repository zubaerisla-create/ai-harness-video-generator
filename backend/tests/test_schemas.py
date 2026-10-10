import pytest
from pydantic import ValidationError
from backend.app.schemas.video import JobCreateRequest, StoryScript, ScenePlanItem

def test_job_create_request_valid():
    req = JobCreateRequest(
        prompt="A brave cat saves a village",
        style="anime",
        requested_duration=120,
        requested_resolution="720p",
        aspect_ratio="9:16"
    )
    assert req.prompt == "A brave cat saves a village"
    assert req.style == "anime"
    assert req.requested_duration == 120

def test_job_create_request_validation_error():
    # Prompt too short (<3 chars)
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="hi")

    # Duration out of bounds (>300s)
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="Valid prompt", requested_duration=500)

def test_story_script_schema():
    script = StoryScript(
        title="Brave Cat",
        synopsis="A brave cat embarks on a journey",
        characters={"Whiskers": "Ginger cat with emerald eyes"},
        scenes=[
            ScenePlanItem(
                sequence_number=1,
                narration_text="In a serene village, Whiskers kept watch over the rooftops.",
                visual_prompt="Anime village rooftops under twilight, a ginger cat gazing into the distance",
                character_continuity="Ginger cat with emerald eyes",
                motion_type="zoom_in",
                transition="fade",
                estimated_duration=12.0
            )
        ]
    )
    assert script.title == "Brave Cat"
    assert len(script.scenes) == 1
    assert script.scenes[0].motion_type == "zoom_in"
