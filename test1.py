import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "satellite-dashboard"))

from orbital import teme_to_geodetic; 
lat, lon, alt = teme_to_geodetic([6778, 0, 0], 2460000.5); 
print('Test:', round(lat, 2), round(lon, 2), round(alt, 1))

import httpx; 
from orbital import propagate_satellite; 
r = httpx.get('https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE'); 
lines = r.text.strip().splitlines(); 
result = propagate_satellite(lines[1], lines[2]); 
print('ISS Lat:', round(result['latitude'], 2), 'Lon:', round(result['longitude'], 2), 'Alt:', round(result['altitude_km'], 1), 'km')