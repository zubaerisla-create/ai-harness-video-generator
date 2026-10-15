import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(String(50), default="business_strategy")
    requested_duration: Mapped[int] = mapped_column(Integer, default=45)
    requested_resolution: Mapped[str] = mapped_column(String(20), default="720p")
    aspect_ratio: Mapped[str] = mapped_column(String(10), default="9:16")
    enable_narration: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_subtitles: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_bgm: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Status & Progress
    # Allowed statuses: pending, processing, ready, uploading, published, failed, cancelled, retry_pending, needs_attention
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # Allowed stages: queued, planning, visuals, narration, subtitles, rendering, validating, ready, uploading, published, done, error
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benchmark_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-encoded benchmark metrics

    # Content & Source Metadata
    content_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sources_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of source URLs

    # Facebook Publishing Fields
    facebook_video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    facebook_post_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scheduled_publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    upload_attempts: Mapped[int] = mapped_column(Integer, default=0)
    upload_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    video: Mapped[Optional["Video"]] = relationship("Video", back_populates="job", uselist=False, cascade="all, delete-orphan")
    scenes: Mapped[List["Scene"]] = relationship("Scene", back_populates="job", order_by="Scene.sequence_number", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("video_jobs.id", ondelete="CASCADE"), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=720)
    height: Mapped[int] = mapped_column(Integer, default=1280)
    fps: Mapped[float] = mapped_column(Float, default=24.0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    job: Mapped["VideoJob"] = relationship("VideoJob", back_populates="video")

class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("video_jobs.id", ondelete="CASCADE"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narration_text: Mapped[str] = mapped_column(Text, nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    visual_backend: Mapped[str] = mapped_column(String(50), default="storyboard_canvas")
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, generated, failed

    # Relationships
    job: Mapped["VideoJob"] = relationship("VideoJob", back_populates="scenes")

class DailyPublication(Base):
    __tablename__ = "daily_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    local_date: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Dhaka")
    published_count: Mapped[int] = mapped_column(Integer, default=0)
    slots_fulfilled: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of fulfilled slots
    video_ids: Mapped[Optional[str]] = mapped_column(Text, default="[]")  # JSON list of published video IDs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
