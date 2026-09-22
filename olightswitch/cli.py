"""omarchy-light-switch — a light theme by day and a dark one at night, on its own.

    omarchy-light-switch setup       pick the two themes and the schedule
    omarchy-light-switch apply       switch to whichever one is right now
    omarchy-light-switch status      what is on, and when it changes next
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

from . import __version__, menu, themes
from .schedule import DARK, LIGHT, Schedule, ScheduleError, next_change, wanted

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                          "omarchy-light-switch")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
WEATHER_FILE = os.path.expanduser("~/.local/state/omarchy/settings/weather.json")
UNIT = "omarchy-light-switch.timer"

ICONS = {"light": "", "dark": "", "clock": "", "sun": "",
         "off": "", "theme": ""}


# ---------------------------------------------------------------- settings

def load() -> tuple[dict, Schedule]:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    schedule = Schedule(
        mode=data.get("mode", "clock"),
        light_at=data.get("light_at", "07:00"),
        dark_at=data.get("dark_at", "19:00"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        offset_minutes=int(data.get("offset_minutes", 0)),
    )
    return data, schedule


def save(data: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, CONFIG_FILE)


def omarchy_location() -> tuple[float, float] | None:
    """Omarchy already knows where you are, if you set the weather location."""
    try:
        with open(WEATHER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return float(data["latitude"]), float(data["longitude"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


# ---------------------------------------------------------------- the switch

def apply(data: dict, schedule: Schedule, now: datetime.datetime | None = None,
          force: bool = False, quiet: bool = False) -> int:
    now = now or datetime.datetime.now().astimezone()
    try:
        want = wanted(schedule, now)
    except ScheduleError as e:
        print(f"omarchy-light-switch: {e}", file=sys.stderr)
        return 2
    theme = data.get(want)
    if not theme:
        print(f"omarchy-light-switch: no {want} theme chosen "
              f"(omarchy-light-switch setup)", file=sys.stderr)
        return 2

    if not force and themes.current() == theme:
        if not quiet:
            print(f"Already on {theme}.")
        return 0
    ok, detail = themes.set_theme(theme)
    if not ok:
        print(f"omarchy-light-switch: {detail}", file=sys.stderr)
        menu.notify("Light switch", detail.splitlines()[0] if detail else "theme change failed")
        return 1
    if not quiet:
        print(f"Switched to {theme} ({want}).")
    return 0


def cmd_apply(args) -> int:
    data, schedule = load()
    return apply(data, schedule, force=args.force, quiet=args.quiet)


def cmd_toggle(args) -> int:
    """Flip to the other one now, without touching the schedule."""
    data, _ = load()
    current = themes.current()
    other = data.get(DARK) if current == data.get(LIGHT) else data.get(LIGHT)
    if not other:
        print("omarchy-light-switch: both themes have to be chosen first "
              "(omarchy-light-switch setup)", file=sys.stderr)
        return 2
    ok, detail = themes.set_theme(other)
    if not ok:
        print(f"omarchy-light-switch: {detail}", file=sys.stderr)
        return 1
    print(f"Switched to {other}.")
    menu.notify("Light switch", f"Now on {other}")
    return 0


def cmd_status(args) -> int:
    data, schedule = load()
    now = datetime.datetime.now().astimezone()
    print(f"light theme    {data.get(LIGHT) or '(not chosen)'}")
    print(f"dark theme     {data.get(DARK) or '(not chosen)'}")
    if schedule.mode == "clock":
        print(f"schedule       clock · light at {schedule.light_at}, "
              f"dark at {schedule.dark_at}")
    else:
        place = f"{schedule.latitude:.3f}, {schedule.longitude:.3f}" \
            if schedule.latitude is not None else "(no location)"
        offset = f" · shifted {schedule.offset_minutes:+d} min" if schedule.offset_minutes else ""
        print(f"schedule       sun · {place}{offset}")
    try:
        want = wanted(schedule, now)
        moment = next_change(schedule, now)
        print(f"right now      {want}")
        print(f"next change    {moment.strftime('%a %H:%M') if moment else 'not this week'}")
    except ScheduleError as e:
        print(f"schedule       INVALID: {e}")
    print(f"current theme  {themes.current() or '?'}")
    print(f"timer          {timer_state()}")
    return 0


def _systemctl(*args: str) -> str:
    """systemctl, or an empty answer where there is no systemd to ask."""
    try:
        r = subprocess.run(["systemctl", "--user", *args], capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.decode("utf-8", "replace").strip()


def timer_state() -> str:
    active = _systemctl("is-active", UNIT) or "unknown"
    enabled = _systemctl("is-enabled", UNIT) or "not installed"
    return f"{active}, {enabled}"


def cmd_enable(args) -> int:
    try:
        r = subprocess.run(["systemctl", "--user", "enable", "--now", UNIT],
                           capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"omarchy-light-switch: {e}", file=sys.stderr)
        return 1
    if r.returncode != 0:
        print(r.stderr.decode("utf-8", "replace").strip(), file=sys.stderr)
        return 1
    print(f"{UNIT} is on — the theme is checked every 15 minutes and after every resume.")
    data, schedule = load()
    return apply(data, schedule)


def cmd_disable(args) -> int:
    _systemctl("disable", "--now", UNIT)
    print(f"{UNIT} is off. The theme stays as it is.")
    return 0


# ---------------------------------------------------------------- setup

def cmd_setup(args) -> int:
    data, schedule = load()
    light = pick_theme("Which theme for the day?", "light", data.get(LIGHT))
    if not light:
        return 1
    dark = pick_theme("Which theme for the night?", "dark", data.get(DARK))
    if not dark:
        return 1
    data[LIGHT], data[DARK] = light, dark

    rows = [(ICONS["clock"], "By the clock", "Two times you choose"),
            (ICONS["sun"], "By the sun", "Sunrise and sunset where you are")]
    pick = menu.select("When should it change?", rows, width=560)
    if not pick:
        return 1

    if pick.startswith("By the clock"):
        data["mode"] = "clock"
        data["light_at"] = menu.ask("Light theme from what time? (07:00)") or "07:00"
        data["dark_at"] = menu.ask("Dark theme from what time? (19:00)") or "19:00"
    else:
        where = omarchy_location()
        if where is None:
            answer = menu.ask("Latitude, longitude (e.g. -23.55, -46.63)")
            try:
                lat, lon = [float(p) for p in (answer or "").replace(";", ",").split(",")[:2]]
            except ValueError:
                print("omarchy-light-switch: that is not a latitude and longitude",
                      file=sys.stderr)
                return 2
            where = (lat, lon)
        data["mode"], data["latitude"], data["longitude"] = "sun", where[0], where[1]

    try:
        _, schedule = load_from(data)
    except ScheduleError as e:
        print(f"omarchy-light-switch: {e}", file=sys.stderr)
        return 2
    save(data)
    print(f"Light: {light}\nDark:  {dark}")
    rc = apply(data, schedule)
    print(f"\nTurn it on with:  omarchy-light-switch enable")
    return rc


def load_from(data: dict) -> tuple[dict, Schedule]:
    schedule = Schedule(mode=data.get("mode", "clock"),
                        light_at=data.get("light_at", "07:00"),
                        dark_at=data.get("dark_at", "19:00"),
                        latitude=data.get("latitude"), longitude=data.get("longitude"),
                        offset_minutes=int(data.get("offset_minutes", 0)))
    schedule.validate()
    return data, schedule


def pick_theme(prompt: str, mode: str, current: str | None) -> str | None:
    matching = themes.by_mode(mode)
    others = [n for n, m in themes.available() if m != mode]
    rows = [(ICONS[mode], name, f"{mode} theme") for name in matching]
    rows += [(ICONS["theme"], name, "the other kind, if you insist") for name in others]
    if not rows:
        print("omarchy-light-switch: no themes found", file=sys.stderr)
        return None
    pick = menu.select(prompt, rows, width=600)
    return pick.split("\t")[0] if pick else None


def cmd_location(args) -> int:
    data, _ = load()
    if args.value:
        try:
            lat, lon = [float(p) for p in args.value.replace(";", ",").split(",")[:2]]
        except ValueError:
            print("omarchy-light-switch: expected \"latitude, longitude\"", file=sys.stderr)
            return 2
        data["latitude"], data["longitude"], data["mode"] = lat, lon, "sun"
        save(data)
    where = (data.get("latitude"), data.get("longitude"))
    if where == (None, None):
        where = omarchy_location() or (None, None)
        if where != (None, None):
            print("(from Omarchy's weather location)")
    if where == (None, None):
        print("No location set. Try: omarchy-light-switch location -- \"-23.55,-46.63\"")
        return 1
    print(f"{where[0]}, {where[1]}")
    return 0


def cmd_menu(args) -> int:
    data, schedule = load()
    rows = [(ICONS["light"], "Switch now", "Flip to the other theme"),
            (ICONS["theme"], "Choose the themes and schedule", "Set it all up"),
            (ICONS["clock"], "Show the schedule", "What is on and what is next")]
    rows.append((ICONS["off"], "Turn the schedule off", "Keep the current theme")
                if "active" in timer_state() else
                (ICONS["sun"], "Turn the schedule on", "Check every 15 minutes"))
    pick = menu.select("Light switch", rows, width=600)
    if not pick:
        return 1
    label = pick.split("\t")[0]
    if label == "Switch now":
        return cmd_toggle(args)
    if label == "Choose the themes and schedule":
        return cmd_setup(args)
    if label == "Turn the schedule on":
        return cmd_enable(args)
    if label == "Turn the schedule off":
        return cmd_disable(args)
    lines = []
    try:
        now = datetime.datetime.now().astimezone()
        moment = next_change(schedule, now)
        lines = [(ICONS["light"], f"Now: {wanted(schedule, now)}", themes.current() or ""),
                 (ICONS["clock"], f"Next: {moment.strftime('%a %H:%M') if moment else '—'}",
                  "when the theme changes")]
    except ScheduleError as e:
        lines = [(ICONS["off"], "The schedule is not valid", str(e))]
    menu.select("Schedule", lines, width=600)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="omarchy-light-switch",
        description="A light theme by day and a dark one at night, on its own.",
        epilog="With no command, the Omarchy menu opens.")
    p.add_argument("command", nargs="?",
                   help="apply, toggle, status, setup, enable, disable, location")
    p.add_argument("value", nargs="?", help="for location: \"latitude, longitude\"")
    p.add_argument("-f", "--force", action="store_true",
                   help="for apply: set the theme even if it is already on")
    p.add_argument("-q", "--quiet", action="store_true", help="for apply: say nothing")
    p.add_argument("-V", "--version", action="version",
                   version=f"omarchy-light-switch {__version__}")
    args = p.parse_args(argv)

    commands = {"apply": cmd_apply, "toggle": cmd_toggle, "status": cmd_status,
                "setup": cmd_setup, "enable": cmd_enable, "disable": cmd_disable,
                "location": cmd_location, "menu": cmd_menu}
    if args.command is None:
        return cmd_menu(args)
    if args.command not in commands:
        print(f"omarchy-light-switch: unknown command {args.command!r}", file=sys.stderr)
        return 2
    try:
        return commands[args.command](args)
    except ScheduleError as e:
        print(f"omarchy-light-switch: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
