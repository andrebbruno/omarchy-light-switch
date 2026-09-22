from olightswitch import themes


def make_theme(base, name, body=""):
    d = base / name
    d.mkdir(parents=True)
    if body:
        (d / "colors.toml").write_text(body, encoding="utf-8")
    return d


def test_the_mode_comes_from_the_theme_itself(tmp_path):
    d = make_theme(tmp_path, "rose-pine-dawn", 'mode = "light"\naccent = "#111111"\n')
    assert themes.mode_of(str(d)) == "light"


def test_the_older_key_is_understood_too(tmp_path):
    d = make_theme(tmp_path, "old-theme", 'theme_type = "light"\n')
    assert themes.mode_of(str(d)) == "light"


def test_a_theme_that_says_nothing_is_taken_as_dark(tmp_path):
    """Which is what Omarchy themes overwhelmingly are."""
    d = make_theme(tmp_path, "quiet", 'accent = "#111111"\n')
    assert themes.mode_of(str(d)) == "dark"


def test_a_theme_with_no_colours_file_at_all(tmp_path):
    d = make_theme(tmp_path, "empty")
    assert themes.mode_of(str(d)) == "dark"


def test_a_light_mode_marker_file_counts(tmp_path):
    d = make_theme(tmp_path, "marked", 'accent = "#111111"\n')
    (d / "light.mode").write_text("", encoding="utf-8")
    assert themes.mode_of(str(d)) == "light"


def test_single_quotes_and_spacing_do_not_matter(tmp_path):
    d = make_theme(tmp_path, "loose", "  mode='LIGHT'  \n")
    assert themes.mode_of(str(d)) == "light"


def test_names_are_shown_the_way_omarchy_shows_them():
    assert themes.pretty("tokyo-night") == "Tokyo Night"
    assert themes.pretty("catppuccin-latte") == "Catppuccin Latte"
    assert themes.pretty("gruvbox") == "Gruvbox"


def test_available_lists_every_theme_with_its_mode(tmp_path):
    user = tmp_path / "user"
    system = tmp_path / "system"
    make_theme(user, "my-theme", 'mode = "light"\n')
    make_theme(system, "tokyo-night", 'mode = "dark"\n')
    make_theme(system, "rose-pine-dawn", 'mode = "light"\n')
    (system / "not-a-theme.txt").write_text("x", encoding="utf-8")

    found = themes.available([str(user), str(system)])
    assert found == [("My Theme", "light"), ("Rose Pine Dawn", "light"),
                     ("Tokyo Night", "dark")]


def test_a_user_theme_wins_over_a_system_one_with_the_same_name(tmp_path):
    user, system = tmp_path / "user", tmp_path / "system"
    make_theme(user, "tokyo-night", 'mode = "light"\n')      # someone's own edit
    make_theme(system, "tokyo-night", 'mode = "dark"\n')
    assert themes.available([str(user), str(system)]) == [("Tokyo Night", "light")]


def test_by_mode_filters(tmp_path):
    system = tmp_path / "system"
    make_theme(system, "a-light", 'mode = "light"\n')
    make_theme(system, "b-dark", 'mode = "dark"\n')
    assert themes.by_mode("light", [str(system)]) == ["A Light"]
    assert themes.by_mode("dark", [str(system)]) == ["B Dark"]


def test_a_missing_themes_directory_is_not_an_error(tmp_path):
    assert themes.available([str(tmp_path / "nowhere")]) == []


def test_the_omarchy_path_is_filled_in_when_the_session_did_not_set_it(monkeypatch):
    """A systemd timer inherits none of the Hyprland session, and omarchy-theme-set
    without OMARCHY_PATH reports that every theme does not exist."""
    monkeypatch.delenv("OMARCHY_PATH", raising=False)
    assert themes._env()["OMARCHY_PATH"] == "/usr/share/omarchy"


def test_a_session_that_does_set_it_is_left_alone(monkeypatch):
    monkeypatch.setenv("OMARCHY_PATH", "/opt/omarchy")
    assert themes._env()["OMARCHY_PATH"] == "/opt/omarchy"


def test_the_theme_command_is_given_that_environment(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["env"] = kwargs.get("env")

        class R:
            returncode = 0
            stdout = b""
            stderr = b""
        return R()

    monkeypatch.delenv("OMARCHY_PATH", raising=False)
    monkeypatch.setattr(themes.subprocess, "run", fake_run)
    themes.set_theme("Tokyo Night")
    assert seen["env"]["OMARCHY_PATH"] == "/usr/share/omarchy"
