import pytest
from pathlib import Path
from fastapi import HTTPException
from backend.app.api.videos import _resolve_safe_file_path
from backend.app.api.auth import get_password_hash, verify_password, create_access_token

def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_path_traversal_protection(tmp_path):
    safe_base = tmp_path / "outputs"
    safe_base.mkdir()
    safe_file = safe_base / "valid_video.mp4"
    safe_file.touch()

    # Valid access within base directory
    resolved = _resolve_safe_file_path(safe_base, str(safe_file))
    assert resolved == safe_file

    # Directory traversal attack: attempting to escape base dir
    malicious_path = str(safe_base / ".." / "etc" / "passwd")
    with pytest.raises(HTTPException) as exc_info:
        _resolve_safe_file_path(safe_base, malicious_path)
    assert exc_info.value.status_code == 403

    # Absolute path outside base directory
    with pytest.raises(HTTPException) as exc_info:
        _resolve_safe_file_path(safe_base, "/etc/shadow")
    assert exc_info.value.status_code == 403
