import zipfile
from types import SimpleNamespace

import pytest

from app.plugin_manager import (
    _validate_public_https_url, duplicate_plugin_groups, geyser_status,
    enable_plugin, install_plugin_file, list_plugins,
)


def make_plugin(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.yml", "name: Example\nversion: 1.0\n")


def test_install_plugin_file_validates_and_installs_atomically(tmp_path):
    server_root = tmp_path / "server"
    source = tmp_path / "example.jar"
    make_plugin(source)

    result = install_plugin_file(SimpleNamespace(directory=str(server_root)), source, "example.jar")

    assert result["name"] == "Example"
    assert (server_root / "plugins" / "example.jar").is_file()


def test_install_plugin_file_rejects_non_plugin_jar(tmp_path):
    source = tmp_path / "not-plugin.jar"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("example.txt", "no metadata")
    with pytest.raises(ValueError, match="plugin.yml"):
        install_plugin_file(SimpleNamespace(directory=str(tmp_path / "server")), source, "bad.jar")


def test_plugin_url_rejects_non_https_before_dns():
    with pytest.raises(ValueError, match="public HTTPS"):
        _validate_public_https_url("http://example.com/plugin.jar")


def test_plugin_url_rejects_private_resolution(monkeypatch):
    monkeypatch.setattr("app.plugin_manager.socket.getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="private network"):
        _validate_public_https_url("https://example.com/plugin.jar")


def test_plugin_info_discovers_yaml_configs_and_geyser_port(tmp_path):
    server_root = tmp_path / "server"
    plugin_dir = server_root / "plugins"
    plugin_dir.mkdir(parents=True)
    source = plugin_dir / "Geyser-Spigot.jar"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("plugin.yml", "name: Geyser-Spigot\nversion: 2.0\n")
    config_dir = plugin_dir / "Geyser-Spigot"
    config_dir.mkdir()
    (config_dir / "config.yml").write_text("bedrock:\n  port: 19132\n")
    (config_dir / "messages.yaml").write_text("hello: world\n")
    (config_dir / "advanced.yml").write_text("feature: true\n")
    (config_dir / "worlds").mkdir()
    (config_dir / "worlds/config.yml").write_text("world: true\n")
    server = SimpleNamespace(directory=str(server_root))

    plugins = list_plugins(server)

    assert plugins[0]["config_files"] == [
        "plugins/Geyser-Spigot/config.yml",
        "plugins/Geyser-Spigot/worlds/config.yml",
        "plugins/Geyser-Spigot/advanced.yml",
        "plugins/Geyser-Spigot/messages.yaml",
    ]
    assert geyser_status(server, plugins) == {
        "installed": True,
        "enabled": True,
        "port": 19132,
    }


def test_duplicate_plugins_only_include_multiple_enabled_versions():
    plugins = [
        {"name": "WorldEdit", "filename": "worldedit-1.jar", "version": "1", "enabled": True},
        {"name": "worldedit", "filename": "worldedit-2.jar", "version": "2", "enabled": True},
        {"name": "WorldEdit", "filename": "worldedit-old.jar.disabled", "version": "0", "enabled": False},
        {"name": "LuckPerms", "filename": "luckperms.jar", "version": "5", "enabled": True},
    ]

    assert duplicate_plugin_groups(plugins) == [{
        "name": "WorldEdit",
        "plugins": [
            {"filename": "worldedit-1.jar", "version": "1"},
            {"filename": "worldedit-2.jar", "version": "2"},
        ],
    }]


def test_duplicate_plugin_groups_include_file_identity_when_available():
    plugins = [
        {
            "name": "Example",
            "filename": "example-1.jar",
            "version": "1",
            "enabled": True,
            "size": 123,
            "modified_ns": "1000",
        },
        {
            "name": "Example",
            "filename": "example-2.jar",
            "version": "2",
            "enabled": True,
            "size": 456,
            "modified_ns": "2000",
        },
    ]

    group = duplicate_plugin_groups(plugins)[0]

    assert group["plugins"][0] == {
        "filename": "example-1.jar",
        "version": "1",
        "size": 123,
        "modified_ns": "1000",
    }


def test_plugin_order_does_not_change_when_enabled(tmp_path):
    server_root = tmp_path / "server"
    plugin_dir = server_root / "plugins"
    plugin_dir.mkdir(parents=True)
    make_plugin(plugin_dir / "zeta.jar")
    make_plugin(plugin_dir / "alpha.jar.disabled")
    server = SimpleNamespace(directory=str(server_root))

    assert [plugin["filename"] for plugin in list_plugins(server)] == [
        "alpha.jar.disabled",
        "zeta.jar",
    ]

    enable_plugin(server, "alpha.jar.disabled")

    assert [plugin["filename"] for plugin in list_plugins(server)] == [
        "alpha.jar",
        "zeta.jar",
    ]
