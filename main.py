import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Query
from redis.asyncio import Redis, ConnectionPool
from prometheus_fastapi_instrumentator import Instrumentator

from schemas import LocationUpdate
from repository import RedisLocationRepository

# 12-Factor App: Load config from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Global variables for connection pool
pool: ConnectionPool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    setup and teardown
    """
    global pool
    pool = ConnectionPool.from_url(REDIS_URL, decode_responses=False)
    yield
    if pool:
        await pool.disconnect()

app = FastAPI(title="FleetTracker Core API", lifespan=lifespan)

# Prometheus Instrumentation
instrumentator = Instrumentator().instrument(app).expose(app)

# Custom Metrics
from prometheus_client import Histogram, Counter

# 監控
# 新增所需時間
GEOADD_LATENCY = Histogram(
    "add_latency",
    "Time spent executing GEOADD in Redis",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# 司機更新次數
DRIVER_UPDATES_TOTAL = Counter(
    "driver_updates_total",
    "Total number of driver location updates",
    ["status"]
)

# Dependency Injection for Redis
async def get_redis() -> Redis:
    if not pool:
        raise RuntimeError("Redis pool not initialized")
    async with Redis(connection_pool=pool) as redis:
        yield redis

# Dependency for Repository
async def get_repository(redis: Redis = Depends(get_redis)) -> RedisLocationRepository:
    return RedisLocationRepository(redis)

@app.post("/v1/locations", status_code=202)
async def update_location(
    update: LocationUpdate, # 定義好的資料格式，FastAPI 會協助轉換
    repo: RedisLocationRepository = Depends(get_repository) # 依賴注入
):
    """
    接收司機位置更新
    """
    DRIVER_UPDATES_TOTAL.labels(status=update.status).inc()
    
    with GEOADD_LATENCY.time():
        await repo.update_location(
            driver_id=update.driver_id,
            lat=update.latitude,
            lon=update.longitude,
            status=update.status
        )
    return {"status": "accepted"}

@app.get("/v1/drivers/nearby")
async def find_nearby_drivers(
    lat: float = Query(..., ge=-90, le=90, description="中心點緯度"),
    lon: float = Query(..., ge=-180, le=180, description="中心點經度"),
    radius_m: int = Query(1000, gt=0, le=10000, description="搜尋半徑(公尺)"),
    repo: RedisLocationRepository = Depends(get_repository) # 依賴注入
):
    """
    搜尋指定半徑內的司機
    """
    drivers = await repo.get_nearby_drivers(lat, lon, radius_m)
    
    return {
        "count": len(drivers),
        "drivers": [
            {"id": driver_id, "distance_m": dist}
            for driver_id, dist in drivers
        ]
    }
