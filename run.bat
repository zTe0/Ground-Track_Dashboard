@echo off
cd /d "%~dp0"

@REM venv\Scripts\activate
@REM source venv_linux/bin/activate

@REM powershell -Command "satellite-dashboard\venv\scripts\activate"
satellite-dashboard\venv\Scripts\python.exe -m test1
cd satellite-dashboard
@REM python -c "from orbital import teme_to_geodetic; lat, lon, alt = teme_to_geodetic([6778, 0, 0], 2460000.5); print('Test:', round(lat, 2), round(lon, 2), round(alt, 1))"
@REM python -c "import httpx; from orbital import propagate_satellite; r = httpx.get('https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE'); lines = r.text.strip().splitlines(); result = propagate_satellite(lines[1], lines[2]); print('ISS Lat:', round(result['latitude'], 2), 'Lon:', round(result['longitude'], 2), 'Alt:', round(result['altitude_km'], 1), 'km')"
@REM venv\Scripts\python.exe -m uvicorn main:app --reload
venv\Scripts\python.exe -m uvicorn main_mirror:app --reload

pause