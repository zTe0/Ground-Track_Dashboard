# Author: Matteo Luciardello Lecardi
import math
from datetime import datetime, timezone, timedelta
from sgp4.api import Satrec, jday

EARTH_RADIUS_KM = 6378.137
EARTH_E2 = 0.00669437999014


def propagate_satellite(tle_line1, tle_line2, dt=None):
    # Create a satellite record from the two TLE lines
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)
    if dt is None:
        dt = datetime.now(timezone.utc)
    # Convert datetime to Julian Date (split into integer day + fraction)
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                  dt.second + dt.microsecond / 1e6)
    # Propagate: returns error code, position (km), velocity (km/s) in TEME frame
    e, r, v = satellite.sgp4(jd, fr)
    if e != 0:
        return None
    # Convert TEME position to latitude, longitude, altitude
    lat, lon, alt = teme_to_geodetic(r, jd + fr)
    # Compute speed magnitude from velocity vector
    speed = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    # Derive orbital period from mean motion (radians per minute)
    period_minutes = (2 * math.pi / satellite.no_kozai) if satellite.no_kozai != 0 else 90.0
    return {
        "latitude": lat,
        "longitude": lon,
        "altitude_km": alt,
        "velocity_km_s": speed,
        "inclination_deg": math.degrees(satellite.inclo),
        "eccentricity": satellite.ecco,
        "period_minutes": period_minutes,
        "epoch": dt.isoformat(),
    }


def greenwich_mean_sidereal_time(jd_ut1):
    # Compute centuries since J2000.0 epoch
    t_ut1 = (jd_ut1 - 2451545.0) / 36525.0
    # Vallado formula: GMST in seconds of time
    gmst_sec = (67310.54841
                + (876600 * 3600 + 8640184.812866) * t_ut1
                + 0.093104 * t_ut1 ** 2
                - 6.2e-6 * t_ut1 ** 3)
    # Convert seconds to radians (43200 seconds = pi radians)
    gmst_rad = math.fmod(gmst_sec * math.pi / 43200.0, 2 * math.pi)
    if gmst_rad < 0:
        gmst_rad += 2 * math.pi
    return gmst_rad


def teme_to_geodetic(r_teme, jd_ut1):
    x, y, z = r_teme
    gmst = greenwich_mean_sidereal_time(jd_ut1)

    # Rotate TEME to ECEF using GMST (z-axis rotation)
    x_ecef = x * math.cos(gmst) + y * math.sin(gmst)
    y_ecef = -x * math.sin(gmst) + y * math.cos(gmst)
    z_ecef = z

    # Compute longitude from ECEF x,y
    lon = math.degrees(math.atan2(y_ecef, x_ecef))
    p = math.sqrt(x_ecef ** 2 + y_ecef ** 2)

    # Iterative latitude computation using WGS-84 ellipsoid
    lat = math.atan2(z_ecef, p)
    for _ in range(5):
        n = EARTH_RADIUS_KM / math.sqrt(1 - EARTH_E2 * math.sin(lat) ** 2)
        lat = math.atan2(z_ecef + EARTH_E2 * n * math.sin(lat), p)

    # Compute altitude above the ellipsoid
    n = EARTH_RADIUS_KM / math.sqrt(1 - EARTH_E2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - n
    lat = math.degrees(lat)

    return lat, lon, alt



def compute_ground_track(tle_line1, tle_line2, steps=90):
    # Create satellite record and compute orbital period
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)
    period_min = (2 * math.pi / satellite.no_kozai) if satellite.no_kozai != 0 else 90.0
    now = datetime.now(timezone.utc)
    track = []
    # Propagate across one full orbit in evenly spaced time steps
    for i in range(steps + 1):
        dt = now + timedelta(minutes=period_min * i / steps)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        e, r, v = satellite.sgp4(jd, fr)
        if e == 0:
            lat, lon, alt = teme_to_geodetic(r, jd + fr)
            track.append({"lat": lat, "lon": lon})
    return track



def compute_elevation(r_teme, jd_ut1, obs_lat, obs_lon, obs_alt_km=0.0):
    gmst = greenwich_mean_sidereal_time(jd_ut1)
    lat_rad = math.radians(obs_lat)
    lon_rad = math.radians(obs_lon)

    # Convert observer geodetic position to ECEF
    n = EARTH_RADIUS_KM / math.sqrt(1 - EARTH_E2 * math.sin(lat_rad) ** 2)
    obs_x = (n + obs_alt_km) * math.cos(lat_rad) * math.cos(lon_rad)
    obs_y = (n + obs_alt_km) * math.cos(lat_rad) * math.sin(lon_rad)
    obs_z = (n * (1 - EARTH_E2) + obs_alt_km) * math.sin(lat_rad)

    # Rotate satellite from TEME to ECEF
    x_ecef = r_teme[0] * math.cos(gmst) + r_teme[1] * math.sin(gmst)
    y_ecef = -r_teme[0] * math.sin(gmst) + r_teme[1] * math.cos(gmst)
    z_ecef = r_teme[2]

    # Compute satellite-observer range vector in ECEF
    dx = x_ecef - obs_x
    dy = y_ecef - obs_y
    dz = z_ecef - obs_z

    # Rotate range vector into South-East-Up topocentric frame
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)

    south = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    east = -sin_lon * dx + cos_lon * dy
    up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz

    # Elevation is the angle above the horizon
    range_km = math.sqrt(south ** 2 + east ** 2 + up ** 2)
    if range_km == 0:
        return 0.0
    elevation = math.degrees(math.asin(up / range_km))
    return elevation

def compute_pass_predictions(tle_line1, tle_line2, obs_lat, obs_lon, obs_alt_km=0.0, hours=24, step_seconds=30):
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)
    now = datetime.now(timezone.utc)
    total_steps = int(hours * 3600 / step_seconds)
    passes = []
    current_pass = None

    for i in range(total_steps):
        dt = now + timedelta(seconds=i * step_seconds)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        e, r, v = satellite.sgp4(jd, fr)
        if e != 0:
            continue
        el = compute_elevation(r, jd + fr, obs_lat, obs_lon, obs_alt_km)

        if el > 10.0:
            # Satellite is above the visibility threshold
            if current_pass is None:
                current_pass = {
                    "rise_time": dt.isoformat(),
                    "max_elevation": el,
                    "max_el_time": dt.isoformat(),
                    "set_time": None,
                }
            elif el > current_pass["max_elevation"]:
                current_pass["max_elevation"] = round(el, 1)
                current_pass["max_el_time"] = dt.isoformat()
        else:
            # Satellite dropped below threshold - end of pass
            if current_pass is not None:
                current_pass["set_time"] = dt.isoformat()
                current_pass["max_elevation"] = round(current_pass["max_elevation"], 1)
                passes.append(current_pass)
                current_pass = None

    return passes