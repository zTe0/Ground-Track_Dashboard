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
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Create the FastAPI application instance
app = FastAPI(title="Satellite Flight Dynamics Dashboard")

# Predefined list of satellites to track (NORAD catalog numbers)
SATELLITES = [
    {"name": "ISS (ZARYA)", "catalog_number": 25544},
    {"name": "HST (Hubble)", "catalog_number": 20580},
    {"name": "NOAA-20", "catalog_number": 43013},
]

# Dictionary to cache fetched TLE data per satellite
TLE_CACHE = {}

async def fetch_tle(catalog_number: int):
    # Return cached TLE if available
    if catalog_number in TLE_CACHE:
        return TLE_CACHE[catalog_number]
    # Fetch fresh TLE from CelesTrak GP API - space stations
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catalog_number}&FORMAT=TLE"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15.0)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch TLE from CelesTrak")
    lines = response.text.strip().splitlines()
    if len(lines) < 3:
        raise HTTPException(status_code=404, detail="TLE not found")
    # Parse the three-line TLE format (name, line1, line2)
    tle_data = {"name": lines[0].strip(), "line1": lines[1].strip(), "line2": lines[2].strip()}
    TLE_CACHE[catalog_number] = tle_data
    return tle_data

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
