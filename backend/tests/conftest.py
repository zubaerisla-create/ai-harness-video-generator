import os
import shutil
import hashlib
import tempfile
import pytest
from pathlib import Path

from backend.app.config import settings
from backend.app.database.session import set_database_url, init_db, engine
from backend.app.models.database import Base

# Operational database path to protect
OPERATIONAL_DB_PATH = Path("./backend/data/harness.db").resolve()
ORIGINAL_DB_URL = settings.DATABASE_URL

# Create dedicated isolated temporary test database directory and file
TEST_TMP_DIR = tempfile.mkdtemp(prefix="ai_harness_isolated_test_")
TEST_DB_PATH = Path(TEST_TMP_DIR) / "isolated_test_harness.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Re-route database connection to isolated test DB immediately before tests load
os.environ["DATABASE_URL"] = TEST_DB_URL
set_database_url(TEST_DB_URL)

def _get_file_checksum(filepath: Path) -> str:
    """Computes SHA-256 hash of a file if it exists."""
    if not filepath.exists():
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

@pytest.fixture(scope="session", autouse=True)
async def isolate_test_database():
    """
    Session-scoped fixture guaranteeing strict test database isolation:
    1. Records sha256 checksum of operational database before tests.
    2. Initializes all tables and migrations in isolated temporary test DB.
    3. Seeds test admin user.
    4. Yields to test suite.
    5. Verifies operational database was NOT touched or modified during testing.
    6. Cleans up temporary test database and restores operational settings.
    """
    # 1. Snapshot operational database state
    op_checksum_before = _get_file_checksum(OPERATIONAL_DB_PATH)
    op_size_before = OPERATIONAL_DB_PATH.stat().st_size if OPERATIONAL_DB_PATH.exists() else 0

    # 2. Ensure test DB uses the isolated URL
    set_database_url(TEST_DB_URL)
    await init_db()

    # 3. Seed default admin user in the isolated test database
    from backend.app.database.session import AsyncSessionLocal
    from backend.app.database.repository import UserRepository
    from backend.app.api.auth import get_password_hash

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        admin = await user_repo.get_by_username(settings.ADMIN_USERNAME)
        if not admin:
            hashed = get_password_hash(settings.ADMIN_PASSWORD)
            await user_repo.create_user(settings.ADMIN_USERNAME, hashed)

    # 4. Run all tests
    yield

    # 5. Teardown: dispose test engine
    from backend.app.database.session import engine as current_engine
    await current_engine.dispose()

    # Clean up temporary test database directory
    shutil.rmtree(TEST_TMP_DIR, ignore_errors=True)

    # Restore operational database engine
    set_database_url(ORIGINAL_DB_URL)

    # 6. Verify operational database integrity
    op_checksum_after = _get_file_checksum(OPERATIONAL_DB_PATH)
    op_size_after = OPERATIONAL_DB_PATH.stat().st_size if OPERATIONAL_DB_PATH.exists() else 0

    assert op_checksum_after == op_checksum_before, (
        f"CRITICAL TEST ISOLATION FAILURE: Operational database '{OPERATIONAL_DB_PATH}' was modified during test run! "
        f"Before: sha256={op_checksum_before[:12]} ({op_size_before}b) -> "
        f"After: sha256={op_checksum_after[:12]} ({op_size_after}b)"
    )

@pytest.fixture(scope="function", autouse=True)
async def enforce_safe_settings_per_test():
    """Ensure safe mode (DRY_RUN=True, FACEBOOK_PUBLISHING_ENABLED=False) is preserved after every test."""
    yield
    settings.FACEBOOK_PUBLISHING_ENABLED = False
    settings.DRY_RUN = True
