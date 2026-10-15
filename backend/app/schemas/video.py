from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class JobCreateRequest(BaseModel):
    prompt: Optional[str] = Field(default="The Future of Artificial Intelligence and Emerging Technology", description="The creative story prompt")
    style: Optional[str] = Field(default="business_strategy", description="Story & visual style: business_strategy, ai_news, sci_fi_concept, emerging_tech, future_predictions")
    requested_duration: Optional[Union[int, str, float]] = Field(default=45, description="Target duration in seconds (15-300)")
    requested_resolution: Optional[str] = Field(default="720p", description="Resolution: 720p or 1080p")
    aspect_ratio: Optional[str] = Field(default="9:16", description="Aspect ratio: 9:16 (vertical), 16:9, or 1:1")
    enable_narration: Optional[Union[bool, str, int]] = Field(default=True, description="Generate audio narration via TTS")
    enable_subtitles: Optional[Union[bool, str, int]] = Field(default=True, description="Render burn-in synchronized subtitles")
    enable_bgm: Optional[Union[bool, str, int]] = Field(default=True, description="Mix royalty-free background music")
    visual_provider: Optional[str] = Field(default=None, description="Override visual provider (storyboard_canvas, comfyui, diffusers)")
    tts_voice: Optional[str] = Field(default=None, description="TTS voice override")

    @field_validator("prompt", mode="before")
    @classmethod
    def validate_prompt(cls, v: Any) -> str:
        if v is None:
            return "The Future of Artificial Intelligence and Emerging Technology"
        s = str(v).strip()
        if len(s) < 3:
            raise ValueError("Prompt must be at least 3 characters long")
        return s

    @field_validator("requested_duration", mode="before")
    @classmethod
    def validate_duration(cls, v: Any) -> int:
        if v is None:
            return 45
        try:
            val = int(float(v))
        except Exception:
            raise ValueError("Duration must be a valid integer")
        if val < 15 or val > 300:
            raise ValueError("Duration must be between 15 and 300 seconds")
        return val

    @field_validator("enable_narration", "enable_subtitles", "enable_bgm", mode="before")
    @classmethod
    def validate_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "t")
        return True

    @field_validator("style", mode="before")
    @classmethod
    def validate_style(cls, v: Any) -> str:
        if not v or not isinstance(v, str):
            return "business_strategy"
        return v.strip().lower()

    @field_validator("requested_resolution", mode="before")
    @classmethod
    def validate_resolution(cls, v: Any) -> str:
        s = str(v or "720p").lower().strip()
        return s if s in ("720p", "1080p") else "720p"

    @field_validator("aspect_ratio", mode="before")
    @classmethod
    def validate_aspect_ratio(cls, v: Any) -> str:
        s = str(v or "9:16").strip()
        return s if s in ("9:16", "16:9", "1:1") else "9:16"

class ScenePlanItem(BaseModel):
    sequence_number: int
    narration_text: str = Field(..., description="Narration spoken for this scene")
    visual_prompt: str = Field(..., description="Visual description for image generation")
    character_continuity: Optional[str] = Field(default="", description="Preserved character appearance attributes")
    motion_type: str = Field(default="zoom_in", description="zoom_in, zoom_out, pan_left, pan_right, slow_push")
    transition: str = Field(default="fade", description="Scene transition: fade, dissolve, wipeleft, etc.")
    estimated_duration: float = Field(default=12.0, description="Target duration for this scene")

class StoryScript(BaseModel):
    title: str = Field(..., description="Compelling short title for the story")
    synopsis: str = Field(..., description="1-2 sentence overall summary")
    characters: Dict[str, Any] = Field(default_factory=dict, description="Character appearance dictionary for visual consistency")
    scenes: List[ScenePlanItem] = Field(..., description="Ordered list of scenes matching target duration")

class SceneResponse(BaseModel):
    id: str
    sequence_number: int
    narration_text: str
    visual_prompt: str
    visual_backend: str
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    duration: float
    status: str

    model_config = {"from_attributes": True}

class VideoResponse(BaseModel):
    id: str
    job_id: str
    title: str
    duration: float
    width: int
    height: int
    fps: float
    file_size: int
    created_at: datetime
    download_url: str
    thumbnail_url: Optional[str] = None

    model_config = {"from_attributes": True}

class JobResponse(BaseModel):
    id: str
    prompt: str
    style: str
    requested_duration: int
    requested_resolution: str
    aspect_ratio: str
    enable_narration: bool
    enable_subtitles: bool
    enable_bgm: bool
    status: str
    progress: int
    stage: str
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    video: Optional[VideoResponse] = None
    scenes: Optional[List[SceneResponse]] = None
    benchmark_data: Optional[Dict[str, Any]] = None
    facebook_video_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None
    published_at: Optional[datetime] = None
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    upload_error: Optional[str] = None

    model_config = {"from_attributes": True}

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class SystemResources(BaseModel):
    cpu_percent: float
    cpu_count: int
    ram_total_gb: float
    ram_used_gb: float
    ram_available_gb: float
    swap_total_gb: float
    swap_used_gb: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    ollama_running: bool
    comfyui_running: bool
    ffmpeg_installed: bool

class SystemStats(BaseModel):
    total_videos: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    processing_jobs: int
    avg_render_time_seconds: float
    disk_free_gb: float
    estimated_daily_throughput: float
