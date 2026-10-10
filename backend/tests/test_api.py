import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.database.session import init_db

@pytest.mark.asyncio
async def test_api_health():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_api_unauthorized_job_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Accessing protected route without credentials must return 401
        resp = await ac.get("/api/jobs")
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_api_login_flow():
    from backend.app.config import settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        })
        assert resp.status_code == 200
        token_data = resp.json()
        assert "access_token" in token_data
        
        # Test authenticated access
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        me_resp = await ac.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == settings.ADMIN_USERNAME
