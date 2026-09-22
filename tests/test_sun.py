import datetime

import pytest

from olightswitch.sun import PolarDay, PolarNight, day_length, sun_times

LONDON = (51.5074, -0.1278)
SAO_PAULO = (-23.5505, -46.6333)
QUITO = (-0.1807, -78.4678)          # on the equator
TROMSO = (69.6492, 18.9553)          # inside the Arctic circle


def at(date, place):
    return sun_times(datetime.date.fromisoformat(date), *place)


def minutes_apart(a, b):
    return abs((a - b).total_seconds()) / 60


# ---------------------------------------------------------------- known places

def test_london_midsummer():
    """21 June 2026 in London: sunrise 04:43 BST, sunset 21:21 BST — 03:43 and 20:21 UTC."""
    rise, set_ = at("2026-06-21", LONDON)
    assert minutes_apart(rise, datetime.datetime(2026, 6, 21, 3, 43,
                                                 tzinfo=datetime.timezone.utc)) < 5
    assert minutes_apart(set_, datetime.datetime(2026, 6, 21, 20, 21,
                                                 tzinfo=datetime.timezone.utc)) < 5


def test_london_midwinter_is_a_short_day():
    length = day_length(datetime.date(2026, 12, 21), *LONDON)
    assert datetime.timedelta(hours=7, minutes=30) < length < datetime.timedelta(hours=8)


def test_sao_paulo_in_january_is_a_long_day():
    """South of the equator the seasons are the other way round."""
    length = day_length(datetime.date(2026, 1, 15), *SAO_PAULO)
    assert length > datetime.timedelta(hours=13)


def test_sao_paulo_in_july_is_a_short_day():
    length = day_length(datetime.date(2026, 7, 15), *SAO_PAULO)
    assert length < datetime.timedelta(hours=11)


def test_the_equator_has_twelve_hour_days_all_year():
    for month in (1, 4, 7, 10):
        length = day_length(datetime.date(2026, month, 15), *QUITO)
        assert abs(length - datetime.timedelta(hours=12)) < datetime.timedelta(minutes=10)


# ---------------------------------------------------------------- invariants

def test_the_equinox_is_twelve_hours_everywhere():
    for place in (LONDON, SAO_PAULO, QUITO):
        length = day_length(datetime.date(2026, 3, 20), *place)
        assert abs(length - datetime.timedelta(hours=12)) < datetime.timedelta(minutes=15)


def test_sunrise_is_always_before_sunset():
    for place in (LONDON, SAO_PAULO, QUITO, (-33.9, 18.4)):
        for month in range(1, 13):
            rise, set_ = sun_times(datetime.date(2026, month, 10), *place)
            assert rise < set_


def test_moving_east_makes_the_sun_rise_earlier():
    earlier, _ = at("2026-05-01", (51.5, 30.0))
    later, _ = at("2026-05-01", (51.5, 0.0))
    assert earlier < later
    # 30° of longitude is two hours of rotation.
    assert 110 < minutes_apart(earlier, later) < 130


def test_a_day_later_moves_the_times_by_about_a_day():
    a, _ = at("2026-05-01", LONDON)
    b, _ = at("2026-05-02", LONDON)
    assert datetime.timedelta(hours=23) < (b - a) < datetime.timedelta(hours=25)


def test_the_times_are_in_utc():
    rise, set_ = at("2026-05-01", LONDON)
    assert rise.tzinfo == datetime.timezone.utc
    assert set_.tzinfo == datetime.timezone.utc


# ---------------------------------------------------------------- the poles

def test_the_arctic_summer_has_no_sunset():
    with pytest.raises(PolarDay):
        at("2026-06-21", TROMSO)


def test_the_arctic_winter_has_no_sunrise():
    with pytest.raises(PolarNight):
        at("2026-12-21", TROMSO)


def test_the_arctic_equinox_is_an_ordinary_day():
    rise, set_ = at("2026-03-20", TROMSO)
    assert rise < set_


def test_the_south_pole_in_june_has_no_sunrise():
    with pytest.raises(PolarNight):
        at("2026-06-21", (-80.0, 0.0))


# ---------------------------------------------------------------- bad input

def test_an_impossible_latitude_is_refused():
    with pytest.raises(ValueError):
        at("2026-05-01", (100.0, 0.0))


def test_an_impossible_longitude_is_refused():
    with pytest.raises(ValueError):
        at("2026-05-01", (0.0, 200.0))
