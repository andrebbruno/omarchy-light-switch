"""Which of the two themes should be on right now, and when that changes next.

A pure decision over a clock and a place: the daemon only has to ask it and obey, and
the whole schedule — including the awkward days around the poles and the switch over
midnight — is testable by handing it a time.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from .sun import PolarDay, PolarNight, sun_times

LIGHT = "light"
DARK = "dark"


class ScheduleError(ValueError):
    pass


@dataclass
class Schedule:
    mode: str = "clock"                  # "clock" or "sun"
    light_at: str = "07:00"
    dark_at: str = "19:00"
    latitude: float | None = None
    longitude: float | None = None
    offset_minutes: int = 0              # shift both sun moments, for early risers

    def validate(self) -> "Schedule":
        if self.mode not in ("clock", "sun"):
            raise ScheduleError(f"unknown mode {self.mode!r} (clock or sun)")
        if self.mode == "clock":
            parse_time(self.light_at)
            parse_time(self.dark_at)
            if parse_time(self.light_at) == parse_time(self.dark_at):
                raise ScheduleError("the two times are the same, so nothing would ever change")
        else:
            if self.latitude is None or self.longitude is None:
                raise ScheduleError("sun mode needs a latitude and a longitude "
                                    "(omarchy-light-switch location)")
        return self


def parse_time(text: str) -> datetime.time:
    """"07:00", "7:00" or "0700" — all the ways someone writes a time of day."""
    raw = (text or "").strip()
    for fmt in ("%H:%M", "%H%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise ScheduleError(f"{text!r} is not a time of day (try 07:00)")


def _on(day: datetime.date, moment: datetime.time,
        tz: datetime.tzinfo | None) -> datetime.datetime:
    return datetime.datetime.combine(day, moment, tzinfo=tz)


def transitions(schedule: Schedule, day: datetime.date,
                tz: datetime.tzinfo | None = None) -> tuple[datetime.datetime | None,
                                                            datetime.datetime | None]:
    """(when light starts, when dark starts) on that day, in local time.

    Either can be None: above the Arctic circle there are days with no sunrise and
    days with no sunset, and the caller has to cope rather than crash.
    """
    schedule.validate()
    if schedule.mode == "clock":
        return (_on(day, parse_time(schedule.light_at), tz),
                _on(day, parse_time(schedule.dark_at), tz))
    try:
        rise, set_ = sun_times(day, schedule.latitude, schedule.longitude)
    except PolarDay:
        return _on(day, datetime.time(0, 0), tz), None          # daylight all day
    except PolarNight:
        return None, _on(day, datetime.time(0, 0), tz)          # night all day
    shift = datetime.timedelta(minutes=schedule.offset_minutes)
    return (rise + shift).astimezone(tz), (set_ + shift).astimezone(tz)


def wanted(schedule: Schedule, now: datetime.datetime) -> str:
    """LIGHT or DARK, for this exact moment."""
    tz = now.tzinfo
    light_at, dark_at = transitions(schedule, now.date(), tz)
    if light_at is None:
        return DARK
    if dark_at is None:
        return LIGHT
    if light_at <= dark_at:
        # The ordinary day: dark, then light in the morning, then dark again at dusk.
        return LIGHT if light_at <= now < dark_at else DARK
    # Someone who wants light in the evening and dark in the morning: the light
    # stretch runs across midnight.
    return DARK if dark_at <= now < light_at else LIGHT


def next_change(schedule: Schedule, now: datetime.datetime) -> datetime.datetime | None:
    """When the answer from `wanted` changes next, looking a week ahead at most."""
    state = wanted(schedule, now)
    tz = now.tzinfo
    for days in range(0, 8):
        day = now.date() + datetime.timedelta(days=days)
        moments = [m for m in transitions(schedule, day, tz) if m is not None]
        for moment in sorted(moments):
            if moment > now and wanted(schedule, moment) != state:
                return moment
    return None
