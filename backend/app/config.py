import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "backend" / "data"
MODELS_DIR = BASE_DIR / "models"
AUDIO_ASSETS_DIR = BASE_DIR / "backend" / "assets" / "music"

# Ensure .venv/bin is in PATH for static ffmpeg/ffprobe binaries
venv_bin = str(BASE_DIR / ".venv" / "bin")
if venv_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "ai-story-harness-insecure-default-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Harness2026!Secure"
    
    # Storage & Paths
    BASE_DIR: Path = BASE_DIR
    OUTPUT_DIR: Path = OUTPUTS_DIR
    TEMP_DIR: Path = OUTPUTS_DIR / "tmp"
    DATA_DIR: Path = DATA_DIR
    MODELS_DIR: Path = MODELS_DIR
    ASSETS_DIR: Path = AUDIO_ASSETS_DIR
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/harness.db"
    
    # Resource Thresholds & Safety
    MIN_DISK_FREE_GB: float = 3.0  # Alert if free space falls below this
    MAX_CONCURRENT_JOBS: int = 1   # Strict limit for 8GB RAM / 2 vCPUs
    JOB_TIMEOUT_SECONDS: int = 1800  # 30 minutes max per job
    
    # Local LLM (Story Planner)
    LLM_PROVIDER: str = "ollama"  # "ollama" or "rule_based"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    LLM_TEMPERATURE: float = 0.7
    LLM_RETRY_COUNT: int = 1
    
    # Visual Generation
    # Options: "ai_diffusion" (unique AI diffusion images per scene),
    #          "storyboard_canvas" (fast deterministic local visual canvas),
    #          "comfyui" (if local ComfyUI instance running on 8188)
    VISUAL_PROVIDER: str = "ai_diffusion"
    COMFYUI_URL: str = "http://127.0.0.1:8188"
    IMAGE_WIDTH: int = 720
    IMAGE_HEIGHT: int = 1280

    # Continuous Auto-Pilot / Daily 5 Videos Target
    AUTOPILOT_ENABLED: bool = True
    AUTOPILOT_DAILY_TARGET: int = 5  # Strictly 5 unique viral short videos per day
    AUTOPILOT_INTERVAL_SECONDS: int = 3600 # Distribute production across the day
    
    # Text-to-Speech (Narration)
    # Options: "piper" (local offline binary/model), "edge_tts" (lightweight cloud fallback if allowed)
    TTS_PROVIDER: str = "piper"
    PIPER_VOICE_MODEL: str = "en_US-lessac-medium"
    PIPER_MODEL_PATH: Path = MODELS_DIR / "piper" / "en_US-lessac-medium.onnx"
    PIPER_CONFIG_PATH: Path = MODELS_DIR / "piper" / "en_US-lessac-medium.onnx.json"
    
    # Video Rendering Defaults (Optimized for Facebook Reels & YouTube Shorts)
    DEFAULT_DURATION_SECONDS: int = 45  # 40-55s optimal for 100% completion & virality
    DEFAULT_ASPECT_RATIO: str = "9:16"
    DEFAULT_WIDTH: int = 720
    DEFAULT_HEIGHT: int = 1280
    DEFAULT_FPS: int = 24
    DEFAULT_VIDEO_BITRATE: str = "3000k"
    DEFAULT_AUDIO_BITRATE: str = "192k"
    DEFAULT_STYLE: str = "business_strategy"  # No anime/cartoons; focus on business, AI, tech, sci-fi
    
    # Motion, Transitions & Sound Effects (Cinematic Editing)
    ENABLE_KEN_BURNS: bool = True
    ENABLE_SUBTITLES: bool = True
    ENABLE_BACKGROUND_MUSIC: bool = True
    BACKGROUND_MUSIC_VOLUME: float = 0.12  # Ducked smoothly under narration
    ENABLE_TRANSITION_SFX: bool = True     # Whooshes, risers & impact drops
    SFX_VOLUME: float = 0.20
    
    # Meta / Facebook Graph API Credentials & Settings
    META_PAGE_ID: str = "1120237794506468"
    META_PAGE_ACCESS_TOKEN: str = ""
    META_APP_ID: str = "3033676750313311"
    META_APP_SECRET: str = ""
    META_GRAPH_API_VERSION: str = "v26.0"

    # Autonomous Scheduling & Facebook Publishing Agent
    TIMEZONE: str = "Asia/Dhaka"
    FACEBOOK_PUBLISHING_ENABLED: bool = False
    DRY_RUN: bool = True
    DAILY_PUBLISH_SLOTS: list[str] = ["09:00", "12:00", "15:00", "18:00", "21:00"]
    MAX_DAILY_PUBLISHED_VIDEOS: int = 5
    ADVANCE_RENDER_MINUTES: int = 60  # Render video up to 60m ahead of scheduled slot

    # Retention
    AUTO_CLEANUP_TEMP_FILES: bool = True
    RETENTION_DAYS: int = 30  # Auto purge older videos if retention enabled
    ENABLE_RETENTION_PURGE: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}

settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
