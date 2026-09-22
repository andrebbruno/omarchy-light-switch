"""Sunrise and sunset, computed rather than fetched.

The NOAA sunrise equation, which is accurate to about a minute and needs nothing but
arithmetic — no network, no API key, no location service. That matters for a tool whose
whole job is to run quietly in the background on a laptop that is often offline.
"""
from __future__ import annotations

import datetime
import math

# The moment the sun's upper limb touches the horizon, allowing for refraction.
HORIZON = -0.833
OBLIQUITY = 23.4397
J2000 = 2451545.0


class PolarDay(Exception):
    """The sun does not set today — above the Arctic circle in June, say."""


class PolarNight(Exception):
    """The sun does not rise today."""


def _julian(date: datetime.date) -> float:
    """The Julian day number for midnight UTC on this date."""
    a = (14 - date.month) // 12
    y = date.year + 4800 - a
    m = date.month + 12 * a - 3
    jdn = (date.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045)
    return jdn - 0.5


def _from_julian(julian: float) -> datetime.datetime:
    seconds = round((julian - J2000) * 86400)
    return (datetime.datetime(2000, 1, 1, 12, tzinfo=datetime.timezone.utc)
            + datetime.timedelta(seconds=seconds))


def sun_times(date: datetime.date, latitude: float, longitude: float
              ) -> tuple[datetime.datetime, datetime.datetime]:
    """(sunrise, sunset) in UTC for that date at that place.

    Raises PolarDay or PolarNight where the sun does not cross the horizon, which is a
    real answer, not an error condition — the caller decides what to do with a day that
    has no dawn.
    """
    if not -90 <= latitude <= 90:
        raise ValueError(f"latitude {latitude} is not between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError(f"longitude {longitude} is not between -180 and 180")

    # The whole number of days since J2000. Leaving the half-day fraction of a
    # midnight-based Julian date in here puts every result twelve hours out.
    n = math.ceil(_julian(date) - J2000 + 0.0008)
    mean_solar = n - longitude / 360.0                       # solar noon, roughly

    anomaly = math.radians((357.5291 + 0.98560028 * mean_solar) % 360)
    centre = (1.9148 * math.sin(anomaly) + 0.0200 * math.sin(2 * anomaly)
              + 0.0003 * math.sin(3 * anomaly))
    ecliptic = math.radians((math.degrees(anomaly) + centre + 180 + 102.9372) % 360)

    transit = (J2000 + mean_solar + 0.0053 * math.sin(anomaly)
               - 0.0069 * math.sin(2 * ecliptic))
    declination = math.asin(math.sin(ecliptic) * math.sin(math.radians(OBLIQUITY)))

    phi = math.radians(latitude)
    numerator = (math.sin(math.radians(HORIZON)) - math.sin(phi) * math.sin(declination))
    denominator = math.cos(phi) * math.cos(declination)
    cos_hour = numerator / denominator if denominator else 2.0
    if cos_hour > 1:
        raise PolarNight(f"the sun does not rise at {latitude:.2f}° on {date}")
    if cos_hour < -1:
        raise PolarDay(f"the sun does not set at {latitude:.2f}° on {date}")

    hour_angle = math.degrees(math.acos(cos_hour))
    return _from_julian(transit - hour_angle / 360), _from_julian(transit + hour_angle / 360)


def local_sun_times(date: datetime.date, latitude: float, longitude: float,
                    tz: datetime.tzinfo | None = None
                    ) -> tuple[datetime.datetime, datetime.datetime]:
    """The same two moments, in the machine's own timezone."""
    rise, set_ = sun_times(date, latitude, longitude)
    return rise.astimezone(tz), set_.astimezone(tz)


def day_length(date: datetime.date, latitude: float, longitude: float) -> datetime.timedelta:
    rise, set_ = sun_times(date, latitude, longitude)
    return set_ - rise
