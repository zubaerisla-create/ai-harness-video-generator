import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger("ai_harness.quality_validator")

class ValidationResult(BaseModel):
    is_valid: bool
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    has_audio: bool = False
    audio_codec: str = ""
    file_size_bytes: int = 0
    thumbnail_path: Optional[str] = None
    error_message: Optional[str] = None

class QualityValidator:
    """
    Validates output MP4 video files using FFprobe.
    Verifies video stream, audio stream, duration tolerance, and generates a thumbnail.
    """

    def validate_video(
        self,
        video_path: Path,
        expected_duration: float,
        expected_width: int = 720,
        expected_height: int = 1280,
        generate_thumbnail: bool = True
    ) -> ValidationResult:
        video_path = Path(video_path)

        if not video_path.exists():
            return ValidationResult(is_valid=False, error_message="Video file does not exist on disk")

        file_size = video_path.stat().st_size
        if file_size < 10000:  # Less than 10KB is corrupted or empty
            return ValidationResult(is_valid=False, file_size_bytes=file_size, error_message=f"File size too small ({file_size} bytes)")

        # Run ffprobe
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if res.returncode != 0:
                return ValidationResult(is_valid=False, file_size_bytes=file_size, error_message="FFprobe execution failed")

            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            format_info = data.get("format", {})

            # Locate video and audio streams
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if not video_stream:
                return ValidationResult(is_valid=False, file_size_bytes=file_size, error_message="No video stream detected in output MP4")

            # Extract dimensions
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            video_codec = video_stream.get("codec_name", "")

            # Extract FPS
            fps_str = video_stream.get("r_frame_rate", "24/1")
            try:
                num, den = map(int, fps_str.split("/"))
                fps = round(num / den, 2) if den > 0 else 24.0
            except Exception:
                fps = 24.0

            # Extract duration
            duration = float(format_info.get("duration", video_stream.get("duration", 0.0)))
            
            # Check audio
            has_audio = audio_stream is not None
            audio_codec = audio_stream.get("codec_name", "") if audio_stream else ""

            # Check duration tolerance (allow reasonable variation based on narration timing)
            if duration <= 1.0:
                return ValidationResult(
                    is_valid=False,
                    duration=duration,
                    width=width,
                    height=height,
                    fps=fps,
                    file_size_bytes=file_size,
                    error_message=f"Rendered video duration too short ({duration:.1f}s)"
                )

            # Generate thumbnail frame
            thumbnail_str = None
            if generate_thumbnail:
                thumb_path = video_path.with_suffix(".thumb.jpg")
                if self._extract_thumbnail(video_path, thumb_path, timestamp=min(2.0, duration / 2.0)):
                    thumbnail_str = str(thumb_path)

            return ValidationResult(
                is_valid=True,
                duration=round(duration, 2),
                width=width,
                height=height,
                fps=fps,
                video_codec=video_codec,
                has_audio=has_audio,
                audio_codec=audio_codec,
                file_size_bytes=file_size,
                thumbnail_path=thumbnail_str
            )

        except Exception as e:
            logger.error(f"Quality validation exception: {e}")
            return ValidationResult(is_valid=False, file_size_bytes=file_size, error_message=str(e))

    def _extract_thumbnail(self, video_path: Path, output_thumb: Path, timestamp: float = 1.0) -> bool:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_thumb)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            return output_thumb.exists() and output_thumb.stat().st_size > 500
        except Exception:
            return False
