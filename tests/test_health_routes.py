from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from core.lifespan import runtime


@pytest.mark.asyncio
async def test_liveness_probe_returns_200() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_probe_healthy() -> None:
    transport = ASGITransport(app=app)
    # Mock db and redis ping to succeed
    with patch("common.database.session.db_manager.ping", new=AsyncMock(return_value=True)):
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        runtime.redis = mock_redis

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "healthy"
            assert data["redis"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_probe_returns_503_when_database_down() -> None:
    transport = ASGITransport(app=app)
    # Mock db ping to fail
    with patch("common.database.session.db_manager.ping", new=AsyncMock(return_value=False)):
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        runtime.redis = mock_redis

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] == "unreachable"
