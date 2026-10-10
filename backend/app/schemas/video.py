from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000, description="The creative story prompt")
    style: str = Field(default="business_strategy", description="Story & visual style: business_strategy, ai_news, sci_fi_concept, emerging_tech, future_predictions")
    requested_duration: int = Field(default=45, ge=15, le=300, description="Target duration in seconds (30-60s optimal for Reels & Shorts)")
    requested_resolution: str = Field(default="720p", description="Resolution: 720p or 1080p")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio: 9:16 (vertical), 16:9, or 1:1")
    enable_narration: bool = Field(default=True, description="Generate audio narration via TTS")
    enable_subtitles: bool = Field(default=True, description="Render burn-in synchronized subtitles")
    enable_bgm: bool = Field(default=True, description="Mix royalty-free background music")
    visual_provider: Optional[str] = Field(default=None, description="Override visual provider (storyboard_canvas, comfyui, diffusers)")
    tts_voice: Optional[str] = Field(default=None, description="TTS voice override")

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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
