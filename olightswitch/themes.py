"""Which themes Omarchy has, and which of them are light.

Every Omarchy theme carries its own answer in colors.toml (`mode = "light"`), so the
light and dark lists come from the themes themselves rather than from a list kept here
that would go stale the moment someone installs a new one.
"""
from __future__ import annotations

import os
import re
import subprocess

USER_THEMES = os.path.expanduser("~/.config/omarchy/themes")
SYSTEM_THEMES = os.path.join(os.environ.get("OMARCHY_PATH") or "/usr/share/omarchy", "themes")

MODE_RE = re.compile(r"""^\s*(?:mode|theme_type)\s*=\s*["']?(light|dark)["']?""",
                     re.IGNORECASE | re.MULTILINE)


def pretty(directory_name: str) -> str:
    """"tokyo-night" -> "Tokyo Night", the way Omarchy's own list shows it."""
    return " ".join(word.capitalize() if word.islower() else word
                    for word in directory_name.split("-"))


def mode_of(theme_dir: str) -> str:
    """"light" or "dark" — defaulting to dark, which is what Omarchy themes mostly are."""
    try:
        with open(os.path.join(theme_dir, "colors.toml"), encoding="utf-8") as f:
            found = MODE_RE.search(f.read())
        if found:
            return found.group(1).lower()
    except OSError:
        pass
    # Some themes signal it with a file beside the colours instead.
    if os.path.exists(os.path.join(theme_dir, "light.mode")):
        return "light"
    return "dark"


def available(dirs: list[str] | None = None) -> list[tuple[str, str]]:
    """[(display name, mode)] for every installed theme, sorted, user themes winning."""
    seen: dict[str, str] = {}
    for base in (dirs if dirs is not None else [USER_THEMES, SYSTEM_THEMES]):
        try:
            entries = sorted(os.listdir(base))
        except OSError:
            continue
        for name in entries:
            path = os.path.join(base, name)
            if not os.path.isdir(path):
                continue
            seen.setdefault(pretty(name), mode_of(path))
    return sorted(seen.items())


def by_mode(mode: str, dirs: list[str] | None = None) -> list[str]:
    return [name for name, m in available(dirs) if m == mode]


def _env() -> dict[str, str]:
    """The environment Omarchy's own scripts expect.

    OMARCHY_PATH is set by the Hyprland session, and a systemd user timer does not
    inherit it — omarchy-theme-set then looks for themes under "/themes" and reports
    that every theme does not exist. Filling it in here is what makes a scheduled
    switch work at all.
    """
    env = dict(os.environ)
    env.setdefault("OMARCHY_PATH", "/usr/share/omarchy")
    env.setdefault("WAYLAND_DISPLAY", "wayland-1")
    return env


def current() -> str:
    """The theme Omarchy says is on, or an empty string where Omarchy is not."""
    try:
        r = subprocess.run(["omarchy-theme-current"], capture_output=True,
                           env=_env(), timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""


def set_theme(name: str) -> tuple[bool, str]:
    """Hand the switch to Omarchy itself, which knows every app that has to be told."""
    try:
        r = subprocess.run(["omarchy-theme-set", name], capture_output=True,
                           env=_env(), timeout=60, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if r.returncode != 0:
        detail = (r.stderr + r.stdout).decode("utf-8", "replace").strip()
        return False, detail or f"omarchy-theme-set exited {r.returncode}"
    return True, ""
