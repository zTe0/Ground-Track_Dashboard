import httpx

FALLBACK_TLES = {
    25544: {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   26158.90128687  .00007994  00000-0  14961-3 0  9996",
        "line2": "2 25544  51.6338 346.0598 0006926 145.2709 214.8733 15.49660544570312"
    }
}

async def run_diagnostics():
    url = "https://pocketworld.org/api/tle-catalog/25544"
    print("--- 1. TESTING NETWORK CONNECTION ---")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
        print(f"Status Code: {response.status_code}")
        
        print("\n--- 2. RAW JSON RESPONSE ---")
        data = response.json()
        print(data)
        
        print("\n--- 3. KEY LOOKUP CHECK ---")
        print(f"Is 'object' key in data? {'object' in data}")
        print(f"Is 'l1' key in data? {'l1' in data}")
        print(f"Is 'l2' key in data? {'l2' in data}")
        
    except Exception as e:
        print(f"Network call failed: {e}")

    print("\n--- 4. FALLBACK DICTIONARY CHECK ---")
    print(f"Keys inside FALLBACK_TLES: {list(FALLBACK_TLES.keys())}")
    print(f"Types of keys inside FALLBACK_TLES: {[type(k) for k in FALLBACK_TLES.keys()]}")
    print(f"Is integer 25544 in FALLBACK_TLES? {25544 in FALLBACK_TLES}")
    print(f"Is string '25544' in FALLBACK_TLES? {'25544' in FALLBACK_TLES}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_diagnostics())