from typing import List, Tuple, Optional
from redis.asyncio import Redis

class RedisLocationRepository:
    """
    跟Redis互動的Repository
    """
    def __init__(self, redis: Redis):
        self.redis = redis
        self.GEO_KEY = "drivers:geo"
        self.META_KEY_PREFIX = "driver:{}:meta"

    async def update_location(self, driver_id: str, lat: float, lon: float, status: str = "online"):
        """
        更新司機位置到 Redis Geo Set (使用 Pipeline 優化效能)
        """
        # 使用 Pipeline 將 3 個指令合併發送，減少網路往返 (RTT)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.geoadd(self.GEO_KEY, (lon, lat, driver_id))
            meta_key = self.META_KEY_PREFIX.format(driver_id)
            pipe.hset(meta_key, mapping={"status": status})
            pipe.expire(meta_key, 60)
            await pipe.execute()

    async def get_nearby_drivers(self, lat: float, lon: float, radius_m: float) -> List[Tuple[str, float]]:
        """
        搜尋附近的司機
        回傳: List of (driver_id, distance_in_meters)
        """
        # 使用 GEOSEARCH 搜尋附近的司機
        # 以 lat, lon 為中心，半徑為 radius_m 的圓形範圍內的司機
        results = await self.redis.geosearch(
            name=self.GEO_KEY,
            longitude=lon,
            latitude=lat,
            radius=radius_m,
            unit="m",
            sort="ASC", # Sort by distance
            withdist=True
        )
        return [(member.decode('utf-8'), dist) for member, dist in results] # 將結果轉換為 (driver_id, distance_in_meters) 的 tuple
