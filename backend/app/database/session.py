from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.config import settings
from backend.app.models.database import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

_sessionmaker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class _AsyncSessionMakerProxy:
    """Proxy object that delegates to _sessionmaker, enabling dynamic engine rebinding."""
    def __call__(self, *args, **kwargs) -> AsyncSession:
        return _sessionmaker(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(_sessionmaker, name)

AsyncSessionLocal = _AsyncSessionMakerProxy()

def set_database_url(new_url: str):
    """
    Dynamically rebinds engine and sessionmaker to a new database URL.
    Used by the test suite to achieve full test database isolation.
    """
    global engine, _sessionmaker
    settings.DATABASE_URL = new_url
    engine = create_async_engine(
        new_url,
        echo=settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False} if "sqlite" in new_url else {}
    )
    _sessionmaker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    return engine

def _run_migrations(connection):
    """Ensure newly added columns exist in SQLite database without requiring external tools."""
    from sqlalchemy import text
    # Check video_jobs table
    try:
        res = connection.execute(text("PRAGMA table_info(video_jobs)")).fetchall()
        existing_cols = {r[1] for r in res}
        columns_to_add = [
            ("content_id", "VARCHAR(64)"),
            ("caption", "TEXT"),
            ("hashtags", "VARCHAR(512)"),
            ("sources_used", "TEXT"),
            ("facebook_video_id", "VARCHAR(64)"),
            ("facebook_post_id", "VARCHAR(64)"),
            ("scheduled_publish_time", "DATETIME"),
            ("published_at", "DATETIME"),
            ("upload_attempts", "INTEGER DEFAULT 0"),
            ("upload_error", "TEXT")
        ]
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                connection.execute(text(f"ALTER TABLE video_jobs ADD COLUMN {col_name} {col_type}"))
    except Exception:
        pass

    # Check videos table
    try:
        res = connection.execute(text("PRAGMA table_info(videos)")).fetchall()
        existing_cols = {r[1] for r in res}
        if "sha256_hash" not in existing_cols:
            connection.execute(text("ALTER TABLE videos ADD COLUMN sha256_hash VARCHAR(64)"))
    except Exception:
        pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_migrations)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
