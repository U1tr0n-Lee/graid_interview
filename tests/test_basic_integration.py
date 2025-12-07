import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from redis.asyncio import ConnectionPool, Redis

from main import app, get_redis
from dotenv import load_dotenv

load_dotenv()

# Fixture to override Redis dependency
@pytest_asyncio.fixture
async def override_redis():
    # Use the running Docker Compose Redis service
    # Note: In a real CI environment, we might want to use a separate DB index (e.g., /1)
    # or flushdb, but for this demo, we use the existing dev DB.
    # Password matches docker-compose.yml / .env
    password = os.getenv("REDIS_PASSWORD", "graid0911")
    url = f"redis://:{password}@localhost:6379/0"
    
    pool = ConnectionPool.from_url(url, decode_responses=False)
    
    # Clean up DB before tests start to ensure isolation
    async with Redis(connection_pool=pool) as r:
        await r.flushdb()
    
    async def get_redis_override():
        async with Redis(connection_pool=pool) as redis:
            yield redis
            
    app.dependency_overrides[get_redis] = get_redis_override
    yield pool
    await pool.disconnect()
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_location(override_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/v1/locations", json={
            "driver_id": "driver_1",
            "latitude": 23.7128,
            "longitude": 120.0060,
            "status": "online"
        })
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}

@pytest.mark.asyncio
async def test_find_nearby_drivers(override_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Insert a driver
        await ac.post("/v1/locations", json={
            "driver_id": "driver_nyc",
            "latitude": 23.7128,
            "longitude": 120.0060,
            "status": "online"
        })
        
        # 2. Search nearby
        response = await ac.get("/v1/drivers/nearby", params={
            "lat": 23.7128,
            "lon": 120.0060,
            "radius_m": 1000
        })
        
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["drivers"][0]["id"] == "driver_nyc"
    # Distance should be very small (approx 0)
    assert data["drivers"][0]["distance_m"] < 10

@pytest.mark.asyncio
async def test_find_nearby_drivers_empty(override_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Search far away
        response = await ac.get("/v1/drivers/nearby", params={
            "lat": 23.7128,
            "lon": 120.0060,
            "radius_m": 1000
        })
        
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
