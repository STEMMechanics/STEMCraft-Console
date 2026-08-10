from types import SimpleNamespace

import pytest

from app.advanced_properties import discover_advanced_properties, save_advanced_property


def server_for(path):
    return SimpleNamespace(directory=str(path))


def test_discovers_and_groups_version_specific_yaml_files(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "world").mkdir()
    (tmp_path / "bukkit.yml").write_text("settings:\n  allow-end: true\n")
    (tmp_path / "spigot.yml").write_text("settings: {}\n")
    (tmp_path / "config/paper-global.yml").write_text("config-version: 31\n")
    (tmp_path / "config/paper-world-defaults.yml").write_text("chunks: {}\n")
    (tmp_path / "world/paper-world.yml").write_text("_version: 31\n")
    (tmp_path / "unrelated.yml").write_text("secret: true\n")

    groups = discover_advanced_properties(server_for(tmp_path))

    assert [group["name"] for group in groups] == [
        "Paper", "Bukkit and Spigot", "World overrides",
    ]
    paths = {item["path"] for group in groups for item in group["files"]}
    assert paths == {
        "bukkit.yml", "spigot.yml", "config/paper-global.yml",
        "config/paper-world-defaults.yml", "world/paper-world.yml",
    }


def test_saves_valid_yaml_without_removing_comments(tmp_path):
    path = tmp_path / "bukkit.yml"
    path.write_text("# keep this comment\nsettings:\n  allow-end: true\n")
    content = "# changed but preserved\nsettings:\n  allow-end: false\n"

    save_advanced_property(server_for(tmp_path), "bukkit.yml", content)

    assert path.read_text() == content


def test_rejects_invalid_yaml_without_changing_file(tmp_path):
    path = tmp_path / "spigot.yml"
    original = "settings:\n  restart-on-crash: true\n"
    path.write_text(original)

    with pytest.raises(ValueError, match="Invalid YAML"):
        save_advanced_property(server_for(tmp_path), "spigot.yml", "settings: [broken\n")

    assert path.read_text() == original


def test_rejects_symlinked_yaml_file(tmp_path):
    outside = tmp_path.parent / "outside.yml"
    outside.write_text("secret: true\n")
    (tmp_path / "bukkit.yml").symlink_to(outside)

    with pytest.raises(ValueError, match="symbolic link"):
        save_advanced_property(server_for(tmp_path), "bukkit.yml", "secret: false\n")
