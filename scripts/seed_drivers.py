import asyncio
import random
import httpx
from datetime import datetime

# 幫助測試，產生大量司機位置更新

# API Configuration
API_URL = "http://localhost:8000/v1/locations"
DRIVER_COUNT = 500

# Taipei City Approx Bounds
TAIPEI_LAT_MIN = 25.00
TAIPEI_LAT_MAX = 25.10
TAIPEI_LON_MIN = 121.45
TAIPEI_LON_MAX = 121.60

async def update_driver(client, index):
    driver_id = f"driver_tpe_{index:03d}"
    lat = random.uniform(TAIPEI_LAT_MIN, TAIPEI_LAT_MAX)
    lon = random.uniform(TAIPEI_LON_MIN, TAIPEI_LON_MAX)
    
    payload = {
        "driver_id": driver_id,
        "latitude": lat,
        "longitude": lon,
        "status": "online"
    }
    
    try:
        resp = await client.post(API_URL, json=payload)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to update {driver_id}: {e}")
        return False

async def main():
    print(f"Starting to seed {DRIVER_COUNT} drivers in Taipei area...")
    start_time = datetime.now()
    
    async with httpx.AsyncClient() as client:
        tasks = [update_driver(client, i) for i in range(DRIVER_COUNT)]
        results = await asyncio.gather(*tasks)
        
    success_count = sum(results)
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"Finished!")
    print(f"Successfully updated: {success_count}/{DRIVER_COUNT}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Rate: {success_count/duration:.2f} req/s")

if __name__ == "__main__":
    asyncio.run(main())
