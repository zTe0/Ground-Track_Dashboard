# Author: Matteo Luciardello Lecardi
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import sys
import os
import uvicorn

from orbital import propagate_satellite, compute_ground_track, compute_pass_predictions

# Helper function to find absolute paths for bundled static assets
def get_resource_path(relative_path):
    try:
        # PyInstaller creates a temporary folder and stores its path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Resolve relative to the actual location of main.py
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Create the FastAPI application instance
# Metadata and GitHub link for the interactive documentation page (/docs)
description = """
An interactive tracking dashboard for space flying bodies. \n
Designed and built with SGP4 propagation of TLEs fetched from CelesTrak.org, TEME-to-Geodetic coordinate rotation, custom NORAD ID.

* **Interactive Map:** [Launch Dashboard Tracker](/)
* **GitHub Repository:** [zTe0/Ground-Track_Dashboard](https://github.com/zTe0/Ground-Track_Dashboard)
* **Author:** Matteo Luciardello Lecardi
"""

# Create the FastAPI application instance
app = FastAPI(
    title="Satellite Ground-Track Dashboard",
    description=description,
    version="1.1.0"
)

# Predefined list of satellites to track (NORAD catalog numbers)
SATELLITES = [
    {"name": "ISS (ZARYA)", "catalog_number": 25544},
    {"name": "HST (Hubble)", "catalog_number": 20580},
    {"name": "NOAA-20", "catalog_number": 43013},
]

# Dictionary to cache fetched TLE data per satellite in memory
TLE_CACHE = {}

# mathematically valid 2026 TLE elements as a bulletproof backup safety net
# FALLBACK_TLES = {}
FALLBACK_TLES = {
    25544: {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   26158.90128687  .00007994  00000-0  14961-3 0  9996",
        "line2": "2 25544  51.6338 346.0598 0006926 145.2709 214.8733 15.49660544570312"
    },
    
    20580: {
        "name": "HST (Hubble)",
        "line1": "1 20580U 90037B   26124.38984173  .00006727  00000-0  21548-3 0  9997",
        "line2": "2 20580  28.4764  19.7915 0002017  24.1737 335.8953 15.30271923781852"
    },
    43013: {
        "name": "NOAA-20",
        "line1": "1 43013U 17073A   26124.15898596  .00000074  00000-0  56168-4 0  9996",
        "line2": "2 43013  98.7754  64.0176 0001977  62.1454 297.9922 14.19549265438228"
    }
}

async def fetch_tle(catalog_number):
    # Force convert catalog_number to an integer to prevent string/int key mismatches
    catalog_number = int(catalog_number)

    # 1. Return cached TLE if available in memory
    if catalog_number in TLE_CACHE:
        return TLE_CACHE[catalog_number]
        
    # 2. Fetch live daily-updated TLE from the PocketWorld API mirror
    url = f"https://pocketworld.org/api/tle/{catalog_number}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=4.0)
            
        if response.status_code == 200:
            data = response.json()
            
            name = None
            line1 = None
            line2 = None
            
            # --- SCHEMA-TOLERANT PARSER ---
            
            # Format A (The specific format you provided: "tle" block and nested "info")
            if "tle" in data and "info" in data and isinstance(data["info"], dict):
                info_block = data["info"]
                name = info_block.get("satname", f"Satellite {catalog_number}")
                tle_str = data.get("tle")
                if tle_str:
                    lines = tle_str.strip().splitlines()
                    if len(lines) >= 2:
                        line1 = lines[0]
                        line2 = lines[1]
                        
            # Format B (Alternative nested "object" format fallback)
            elif "object" in data and isinstance(data["object"], dict):
                obj_data = data["object"]
                name = obj_data.get("n", f"Satellite {catalog_number}")
                line1 = obj_data.get("l1")
                line2 = obj_data.get("l2")
            
            # STRICT VALIDATION: Ensure none of the parsed fields are empty
            if name and line1 and line2:
                tle_data = {
                    "name": str(name).strip(),
                    "line1": str(line1).strip(),
                    "line2": str(line2).strip()
                }
                # Cache and return the live elements
                TLE_CACHE[catalog_number] = tle_data
                print(f"Successfully retrieved live TLE for {catalog_number} from PocketWorld.")
                return tle_data
            else:
                raise ValueError("Response JSON format could not be parsed.")
                
    except Exception as e:
        # Catch connection timeouts or blocks silently, log to console
        print(f"PocketWorld mirror failed or timed out ({e}). Loading fallback cache.")

    # 3. Safe fallback in case of connection loss or timeout
    if catalog_number in FALLBACK_TLES:
        fallback_data = FALLBACK_TLES[catalog_number]
        TLE_CACHE[catalog_number] = fallback_data
        print(f"Successfully loaded safe fallback TLE for {catalog_number}.")
        return fallback_data

    raise HTTPException(status_code=502, detail="Failed to fetch TLE and no fallback available")

@app.get("/api/satellites")
async def list_satellites_example():
    return SATELLITES


@app.get("/api/satellite/{catalog_number}")
async def get_satellite_position(catalog_number: int):
    tle = await fetch_tle(catalog_number)
    result = propagate_satellite(tle["line1"], tle["line2"])
    if result is None:
        raise HTTPException(status_code=500, detail="Propagation error")
    result["name"] = tle["name"]
    return result


@app.get("/api/satellite/{catalog_number}/track")
async def get_ground_track(catalog_number: int):
    tle = await fetch_tle(catalog_number)
    track = compute_ground_track(tle["line1"], tle["line2"])
    return {"name": tle["name"], "track": track}


@app.get("/api/satellite/{catalog_number}/passes")
async def get_passes(catalog_number: int, lat: float = 0.0, lon: float = 0.0):
    tle = await fetch_tle(catalog_number)
    passes = compute_pass_predictions(tle["line1"], tle["line2"], lat, lon)
    return {"name": tle["name"], "passes": passes}


# Mount static files using the path helper
static_dir = get_resource_path("static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Serve index.html using the path helper
@app.get("/")
async def root():
    index_path = get_resource_path("static/index.html")
    return FileResponse(index_path)

# Programmatic startup so running the .exe starts the server
if __name__ == "__main__":
    # Disable reload when packaged, specify host and port
    uvicorn.run(app, host="127.0.0.1", port=8000)
