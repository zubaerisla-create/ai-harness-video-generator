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
        resp = await ac.get("/api/auth/me")
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

@pytest.mark.asyncio
async def test_facebook_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test status endpoint
        status_resp = await ac.get("/api/facebook/status")
        assert status_resp.status_code == 200
        s_data = status_resp.json()
        assert "page_connected" in s_data
        assert "daily_target" in s_data
        assert s_data["timezone"] == "Asia/Dhaka"
        assert len(s_data["slots"]) == 5

        # Test daily summary endpoint
        summary_resp = await ac.get("/api/facebook/daily-summary")
        assert summary_resp.status_code == 200
        sum_data = summary_resp.json()
        assert sum_data["daily_target"] == 5
        assert "published_count" in sum_data
        assert "slots_fulfilled" in sum_data

        # Test toggle dry run endpoint
        dry_resp = await ac.post("/api/facebook/dry-run", json={"enabled": True})
        assert dry_resp.status_code == 200
        assert dry_resp.json()["dry_run"] is True
