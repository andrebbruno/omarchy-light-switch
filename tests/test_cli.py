import datetime
import json

import pytest

from olightswitch import cli
from olightswitch.schedule import Schedule

TZ = datetime.timezone(datetime.timedelta(hours=-3))


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(cli, "WEATHER_FILE", str(tmp_path / "weather.json"))
    monkeypatch.setattr(cli.menu, "notify", lambda *a, **k: None)
    switched = []
    monkeypatch.setattr(cli.themes, "set_theme",
                        lambda name: (switched.append(name), (True, ""))[1])
    monkeypatch.setattr(cli.themes, "current", lambda: switched[-1] if switched else "Nothing")
    return tmp_path, switched


def write_config(tmp_path, **data):
    (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")


def test_defaults_when_there_is_no_config(home):
    _, schedule = cli.load()
    assert schedule.mode == "clock"
    assert schedule.light_at == "07:00"


def test_a_corrupt_config_falls_back_to_the_defaults(home):
    tmp_path, _ = home
    (tmp_path / "config.json").write_text("{not json", encoding="utf-8")
    data, schedule = cli.load()
    assert data == {} and schedule.mode == "clock"


def test_apply_switches_to_the_day_theme_in_the_morning(home):
    tmp_path, switched = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    data, schedule = cli.load()
    assert cli.apply(data, schedule, now=datetime.datetime(2026, 5, 15, 9, tzinfo=TZ)) == 0
    assert switched == ["Rose Pine Dawn"]


def test_apply_switches_to_the_night_theme_after_dark(home):
    tmp_path, switched = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    data, schedule = cli.load()
    assert cli.apply(data, schedule, now=datetime.datetime(2026, 5, 15, 21, tzinfo=TZ)) == 0
    assert switched == ["Tokyo Night"]


def test_apply_does_nothing_when_the_theme_is_already_right(home):
    tmp_path, switched = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    data, schedule = cli.load()
    morning = datetime.datetime(2026, 5, 15, 9, tzinfo=TZ)
    cli.apply(data, schedule, now=morning)
    cli.apply(data, schedule, now=morning)
    assert switched == ["Rose Pine Dawn"]          # the second call was a no-op


def test_apply_can_be_forced(home):
    tmp_path, switched = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    data, schedule = cli.load()
    morning = datetime.datetime(2026, 5, 15, 9, tzinfo=TZ)
    cli.apply(data, schedule, now=morning)
    cli.apply(data, schedule, now=morning, force=True)
    assert switched == ["Rose Pine Dawn", "Rose Pine Dawn"]


def test_apply_without_themes_chosen_says_so(home, capsys):
    data, schedule = cli.load()
    assert cli.apply(data, schedule) == 2
    assert "no" in capsys.readouterr().err


def test_apply_reports_a_failed_theme_change(home, monkeypatch, capsys):
    tmp_path, _ = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    monkeypatch.setattr(cli.themes, "set_theme", lambda name: (False, "no such theme"))
    monkeypatch.setattr(cli.themes, "current", lambda: "Something Else")
    data, schedule = cli.load()
    assert cli.apply(data, schedule) == 1
    assert "no such theme" in capsys.readouterr().err


def test_toggle_flips_to_the_other_theme(home):
    tmp_path, switched = home
    write_config(tmp_path, light="Rose Pine Dawn", dark="Tokyo Night")
    switched.append("Rose Pine Dawn")              # pretend we are on the light one
    assert cli.main(["toggle"]) == 0
    assert switched[-1] == "Tokyo Night"
    assert cli.main(["toggle"]) == 0
    assert switched[-1] == "Rose Pine Dawn"


def test_toggle_needs_both_themes(home, capsys):
    assert cli.main(["toggle"]) == 2


def test_sun_mode_uses_omarchys_weather_location(home):
    tmp_path, _ = home
    (tmp_path / "weather.json").write_text(
        json.dumps({"name": "Sao Paulo", "latitude": -23.55, "longitude": -46.63}),
        encoding="utf-8")
    assert cli.omarchy_location() == (-23.55, -46.63)


def test_a_weather_file_without_coordinates_is_not_a_location(home):
    tmp_path, _ = home
    (tmp_path / "weather.json").write_text(json.dumps({"name": "Malibu"}), encoding="utf-8")
    assert cli.omarchy_location() is None


def test_location_stores_what_it_is_given(home, capsys):
    assert cli.main(["location", "-23.55, -46.63"]) == 0
    data, schedule = cli.load()
    assert (data["latitude"], data["longitude"]) == (-23.55, -46.63)
    assert schedule.mode == "sun"


def test_location_refuses_nonsense(home, capsys):
    assert cli.main(["location", "somewhere nice"]) == 2


def test_status_runs_with_an_empty_config(home, capsys):
    assert cli.main(["status"]) == 0
    assert "not chosen" in capsys.readouterr().out


def test_status_shows_the_next_change(home, capsys):
    tmp_path, _ = home
    write_config(tmp_path, light="A", dark="B", mode="clock",
                 light_at="07:00", dark_at="19:00")
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "next change" in out and "light at 07:00" in out


def test_an_unknown_command_is_reported(home, capsys):
    assert cli.main(["frobnicate"]) == 2


def test_an_invalid_schedule_is_reported_by_status(home, capsys):
    tmp_path, _ = home
    write_config(tmp_path, light="A", dark="B", mode="sun")     # no coordinates
    assert cli.main(["status"]) == 0
    assert "INVALID" in capsys.readouterr().out
