import pytest
from pathlib import Path
from backend.app.services.subtitle_generator import SubtitleGenerator

def test_subtitle_generator_srt_and_ass(tmp_path):
    sub_gen = SubtitleGenerator()
    scenes = [
        {
            "sequence_number": 1,
            "start_time": 0.0,
            "duration": 10.0,
            "narration_text": "In a peaceful village far away, a curious cat watched the stars every single night."
        },
        {
            "sequence_number": 2,
            "start_time": 10.0,
            "duration": 12.0,
            "narration_text": "One day, a mysterious falling star landed right beside the quiet pond."
        }
    ]

    srt_path = tmp_path / "test.srt"
    ass_path = tmp_path / "test.ass"

    res_srt = sub_gen.generate_srt(scenes, srt_path)
    res_ass = sub_gen.generate_ass(scenes, ass_path, width=720, height=1280)

    assert res_srt.exists()
    assert res_ass.exists()

    srt_content = res_srt.read_text(encoding="utf-8")
    assert "-->" in srt_content
    assert "peaceful village" in srt_content

    ass_content = res_ass.read_text(encoding="utf-8")
    assert "[Script Info]" in ass_content
    assert "[V4+ Styles]" in ass_content
    assert "Dialogue: 0," in ass_content
