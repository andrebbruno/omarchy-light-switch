import datetime

import pytest

from olightswitch.schedule import (DARK, LIGHT, Schedule, ScheduleError, next_change,
                                   parse_time, transitions, wanted)

TZ = datetime.timezone(datetime.timedelta(hours=-3))       # São Paulo, no DST
LONDON = dict(mode="sun", latitude=51.5074, longitude=-0.1278)


def at(hour, minute=0, day=15, month=5):
    return datetime.datetime(2026, month, day, hour, minute, tzinfo=TZ)


# ---------------------------------------------------------------- the clock

def test_the_ordinary_day():
    s = Schedule(light_at="07:00", dark_at="19:00")
    assert wanted(s, at(6, 59)) == DARK
    assert wanted(s, at(7, 0)) == LIGHT
    assert wanted(s, at(12)) == LIGHT
    assert wanted(s, at(18, 59)) == LIGHT
    assert wanted(s, at(19, 0)) == DARK
    assert wanted(s, at(23, 30)) == DARK


def test_a_light_stretch_that_crosses_midnight():
    """Someone who works nights and wants the light theme from 8pm to 6am."""
    s = Schedule(light_at="20:00", dark_at="06:00")
    assert wanted(s, at(21)) == LIGHT
    assert wanted(s, at(2)) == LIGHT
    assert wanted(s, at(5, 59)) == LIGHT
    assert wanted(s, at(6, 0)) == DARK
    assert wanted(s, at(12)) == DARK


def test_times_can_be_written_several_ways():
    assert parse_time("7:00") == datetime.time(7, 0)
    assert parse_time("07:00") == datetime.time(7, 0)
    assert parse_time("0700") == datetime.time(7, 0)
    assert parse_time(" 19:30:00 ") == datetime.time(19, 30)


def test_a_time_that_is_not_a_time_is_refused():
    for bad in ("", "noon", "25:00", "7", "7pm"):
        with pytest.raises(ScheduleError):
            parse_time(bad)


def test_two_identical_times_are_refused():
    with pytest.raises(ScheduleError):
        Schedule(light_at="07:00", dark_at="07:00").validate()


def test_an_unknown_mode_is_refused():
    with pytest.raises(ScheduleError):
        Schedule(mode="vibes").validate()


def test_sun_mode_without_a_place_is_refused():
    with pytest.raises(ScheduleError) as e:
        Schedule(mode="sun").validate()
    assert "latitude" in str(e.value)


# ---------------------------------------------------------------- the sun

def test_sun_mode_is_light_at_noon_and_dark_at_midnight():
    s = Schedule(**LONDON)
    assert wanted(s, datetime.datetime(2026, 5, 15, 12, tzinfo=datetime.timezone.utc)) == LIGHT
    assert wanted(s, datetime.datetime(2026, 5, 15, 1, tzinfo=datetime.timezone.utc)) == DARK


def test_sun_mode_follows_the_season():
    """In London the light theme lasts far longer in June than in December."""
    s = Schedule(**LONDON)
    utc = datetime.timezone.utc
    june = datetime.datetime(2026, 6, 21, 20, tzinfo=utc)
    december = datetime.datetime(2026, 12, 21, 20, tzinfo=utc)
    assert wanted(s, june) == LIGHT
    assert wanted(s, december) == DARK


def test_the_offset_shifts_both_moments():
    early = Schedule(**LONDON, offset_minutes=-60)
    utc = datetime.timezone.utc
    plain_rise, _ = transitions(Schedule(**LONDON), datetime.date(2026, 5, 15), utc)
    early_rise, _ = transitions(early, datetime.date(2026, 5, 15), utc)
    assert (plain_rise - early_rise) == datetime.timedelta(minutes=60)


def test_a_polar_day_stays_light():
    s = Schedule(mode="sun", latitude=69.65, longitude=18.96)
    assert wanted(s, datetime.datetime(2026, 6, 21, 2, tzinfo=datetime.timezone.utc)) == LIGHT


def test_a_polar_night_stays_dark():
    s = Schedule(mode="sun", latitude=69.65, longitude=18.96)
    assert wanted(s, datetime.datetime(2026, 12, 21, 12, tzinfo=datetime.timezone.utc)) == DARK


# ---------------------------------------------------------------- next change

def test_the_next_change_in_the_morning():
    s = Schedule(light_at="07:00", dark_at="19:00")
    assert next_change(s, at(6)) == at(7)


def test_the_next_change_in_the_evening():
    s = Schedule(light_at="07:00", dark_at="19:00")
    assert next_change(s, at(12)) == at(19)


def test_after_the_last_change_it_rolls_to_tomorrow():
    s = Schedule(light_at="07:00", dark_at="19:00")
    assert next_change(s, at(20)) == at(7, day=16)


def test_the_next_change_in_sun_mode_is_a_real_moment():
    s = Schedule(**LONDON)
    now = datetime.datetime(2026, 5, 15, 12, tzinfo=datetime.timezone.utc)
    moment = next_change(s, now)
    assert moment is not None and moment > now
    assert wanted(s, moment) == DARK


def test_a_polar_night_has_no_next_change_this_week():
    s = Schedule(mode="sun", latitude=80.0, longitude=0.0)
    now = datetime.datetime(2026, 12, 21, 12, tzinfo=datetime.timezone.utc)
    assert next_change(s, now) is None
