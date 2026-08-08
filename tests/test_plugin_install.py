import zipfile
from types import SimpleNamespace

import pytest

from app.plugin_manager import _validate_public_https_url, geyser_status, install_plugin_file, list_plugins


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
    server = SimpleNamespace(directory=str(server_root))

    plugins = list_plugins(server)

    assert plugins[0]["config_files"] == [
        "plugins/Geyser-Spigot/config.yml",
        "plugins/Geyser-Spigot/messages.yaml",
    ]
    assert geyser_status(server, plugins) == {
        "installed": True,
        "enabled": True,
        "port": 19132,
    }
