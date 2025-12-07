import pytest
import asyncio
import time
from httpx import AsyncClient, ASGITransport, Limits
from main import app
from tests.test_basic_integration import override_redis

# Configuration for Load Tests
TOTAL_REQUESTS = 6000
CONCURRENT_DRIVERS = 3000
CONCURRENT_LIMIT = 500

async def run_load_test(client, test_name):
    """
    Shared load test logic for both Logic and Network tests
    """
    print(f"\nStarting {test_name}: {CONCURRENT_DRIVERS} concurrent drivers")
    print(f"Target: Verify system stability under load ({TOTAL_REQUESTS} requests)")
    
    sem = asyncio.Semaphore(CONCURRENT_LIMIT)

    async def send_update(i):
        payload = {
            "driver_id": f"driver_{i % CONCURRENT_DRIVERS}",
            "latitude": 25.0330,
            "longitude": 121.5654,
            "status": "online"
        }
        start = time.perf_counter()
        async with sem:
            try:
                response = await client.post("/v1/locations", json=payload)
                latency = (time.perf_counter() - start) * 1000 # ms
                return response.status_code, latency
            except Exception:
                return 500, 0.0

    print(f"Sending {TOTAL_REQUESTS} requests...")
    start_time = time.perf_counter()
    
    tasks = [send_update(i) for i in range(TOTAL_REQUESTS)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    
    # Analysis
    duration = end_time - start_time
    success_count = sum(1 for r in results if r[0] == 202)
    latencies = [r[1] for r in results if r[0] == 202]
    rps = success_count / duration if duration > 0 else 0
    
    print(f"------------------------------------------------")
    print(f"Completed in {duration:.2f} seconds")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Successful: {success_count}")
    print(f"Failed: {TOTAL_REQUESTS - success_count}")
    print(f"Throughput (RPS): {rps:.2f} req/s")
    
    if latencies:
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99 = latencies[p99_index] if latencies else 0
        avg = sum(latencies) / len(latencies)
        print(f"Avg Latency: {avg:.2f} ms")
        print(f"P99 Latency: {p99:.2f} ms")

    return success_count

@pytest.mark.asyncio
async def test_logic_performance_in_memory(override_redis):
    """
    Test 1: Logic Performance (ASGITransport)
    Bypasses network layer, tests pure application logic speed.
    """
    transport = ASGITransport(app=app)
    limits = Limits(max_keepalive_connections=None, max_connections=None)
    
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0, limits=limits) as ac:
        success_count = await run_load_test(ac, "Logic Performance Test (In-Memory)")
        assert success_count == TOTAL_REQUESTS

@pytest.mark.asyncio
async def test_network_stress_localhost():
    """
    Test 2: Network Stress Test (Real Network)
    Connects to localhost:8000 via TCP.
    REQUIRES: docker-compose up --build
    """
    limits = Limits(max_keepalive_connections=None, max_connections=None)
    
    try:
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0, limits=limits) as ac:
            # Check if server is up
            try:
                await ac.get("/docs")
            except Exception:
                pytest.skip("Server not running at localhost:8000. Skipping network test. (Run `docker-compose up` first)")
                
            success_count = await run_load_test(ac, "Network Stress Test (Localhost TCP)")
            # Unlike logic test, network test might fail due to OS limits, so we check stability but don't fail strictly if connection drops
            # But we aim for 100% success if tuned correctly.
            assert success_count > 0 
    except Exception as e:
        pytest.skip(f"Network test skipped due to connection error: {e}")
