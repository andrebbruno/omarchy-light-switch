# Light Switch for Omarchy

A light theme by day and a dark one at night, on its own. A port of
[PowerToys Light Switch](https://learn.microsoft.com/windows/powertoys/light-switch) to
[Omarchy](https://omarchy.org) — by the clock, or by the actual sunrise where you are.

*[Leia em português](README.pt-BR.md)*

```bash
omarchy-light-switch setup      # pick the two themes and the schedule
omarchy-light-switch enable     # let it run
omarchy-light-switch toggle     # flip now, without touching the schedule
```

## How it decides

**By the clock** — two times you choose. A light stretch that crosses midnight works too,
for people who want the light theme in the evening.

**By the sun** — sunrise and sunset computed for your coordinates. No network, no API key,
no location service: it is the NOAA sunrise equation, accurate to about a minute, and it
reuses the location Omarchy already has for the weather panel if you set one there. An
`offset_minutes` shifts both moments, for people who are up before the sun.

Either way, `apply` is idempotent: it asks which theme should be on, and does nothing at all
when that is already the answer. That is what makes it safe to run on a timer.

## Which themes are light?

The themes say so themselves — every Omarchy theme's `colors.toml` carries
`mode = "light"` or `mode = "dark"`, so the setup menu offers the right ones without a list
that would go stale the moment you install a new theme.

## Install

### Arch / Omarchy

```bash
sudo pacman -U omarchy-light-switch-*-any.pkg.tar.zst   # from Releases
omarchy-light-switch setup
omarchy-light-switch enable
```

`enable` turns on a user timer that checks every 15 minutes and again after every resume, so
a laptop that was asleep at sunset is right again when it wakes up.

A keybinding for the manual flip, in `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + T", "Light/dark", "omarchy-light-switch toggle")
```

### Elsewhere

`pipx install git+https://github.com/andrebbruno/omarchy-light-switch`. It drives
`omarchy-theme-set`, so it wants Omarchy; the sunrise maths is useful anywhere.

## Commands

```
omarchy-light-switch                 the menu
omarchy-light-switch setup           choose the themes and the schedule
omarchy-light-switch apply           switch to whichever theme is right now
omarchy-light-switch toggle          flip to the other one
omarchy-light-switch status          what is on, and when it changes next
omarchy-light-switch enable|disable  the timer
omarchy-light-switch location "-23.55, -46.63"
```

`~/.config/omarchy-light-switch/config.json`:

```json
{
  "light": "Catppuccin Latte",
  "dark": "Tokyo Night",
  "mode": "sun",
  "latitude": -23.55,
  "longitude": -46.63,
  "offset_minutes": -30
}
```

## ⚠️ A systemd timer inherits none of your session

That is not a footnote, it is the bug this tool was written around: `OMARCHY_PATH` is set by
the Hyprland session, a user timer does not get it, and `omarchy-theme-set` without it reports
that *every* theme does not exist. It is filled in here before the theme is changed, which is
why the scheduled switch works and not just the one you run from a terminal.

## Development

```bash
python -m pytest tests -q     # 65 tests, no clock watching required
```

The sunrise equation (`olightswitch/sun.py`) and the decision about which theme should be on
(`olightswitch/schedule.py`) are pure functions over a time and a place, so the tests check
London's midsummer sunrise to the minute, twelve-hour days on the equator, the polar day and
the polar night, and a light stretch that runs across midnight.

## License

MIT © Andre Bruno
