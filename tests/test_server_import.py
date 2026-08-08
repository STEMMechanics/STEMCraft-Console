from pathlib import Path
import zipfile

from app import server_import
from app.web_servers import router as web_servers_router
from starlette.routing import Match


def make_server(directory: Path, *, port=25565, eula=True):
    directory.mkdir(parents=True)
    with zipfile.ZipFile(directory / "paper.jar", "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
    (directory / "server.properties").write_text(f"server-port={port}\n")
    if eula:
        (directory / "eula.txt").write_text("eula=true\n")


def allow_environment(monkeypatch):
    monkeypatch.setattr(server_import, "find_systemd_service", lambda _path, _records=None: None)
    monkeypatch.setattr(server_import, "systemd_service_records", lambda: [])
    monkeypatch.setattr(server_import, "_port_available", lambda _port: True)


def test_inspection_accepts_manageable_external_server(tmp_path, monkeypatch):
    directory = tmp_path / "opt" / "minecraft"
    make_server(directory, port=25570)
    allow_environment(monkeypatch)

    result = server_import.inspect_server_directory(directory, verify_write=True)

    assert result["ready"] is True
    assert result["jar_name"] == "paper.jar"
    assert result["port"] == 25570
    assert result["errors"] == []


def test_inspection_reports_missing_required_files(tmp_path, monkeypatch):
    directory = tmp_path / "empty"
    directory.mkdir()
    allow_environment(monkeypatch)

    result = server_import.inspect_server_directory(directory)

    assert result["ready"] is False
    assert "server.properties was not found" in result["errors"]
    assert "No server JAR was found in the directory" in result["errors"]


def test_inspection_blocks_active_external_service(tmp_path, monkeypatch):
    directory = tmp_path / "minecraft"
    make_server(directory)
    monkeypatch.setattr(
        server_import,
        "find_systemd_service",
        lambda _path, _records=None: {"unit": "minecraft.service", "active": True, "enabled": True},
    )
    monkeypatch.setattr(server_import, "_port_available", lambda _port: False)

    result = server_import.inspect_server_directory(directory)

    assert result["ready"] is False
    assert any("minecraft.service is active" in error for error in result["errors"])


def test_inspection_warns_about_eula_and_disabled_service(tmp_path, monkeypatch):
    directory = tmp_path / "minecraft"
    make_server(directory, eula=False)
    monkeypatch.setattr(
        server_import,
        "find_systemd_service",
        lambda _path, _records=None: {"unit": "minecraft.service", "active": False, "enabled": False},
    )
    monkeypatch.setattr(server_import, "_port_available", lambda _port: True)

    result = server_import.inspect_server_directory(directory)

    assert result["ready"] is True
    assert any("EULA" in warning for warning in result["warnings"])
    assert any("Disabled external service" in warning for warning in result["warnings"])


def test_scan_detects_nested_servers_and_skips_managed_paths(tmp_path, monkeypatch):
    root = tmp_path / "servers"
    first = root / "network" / "survival"
    second = root / "creative"
    make_server(first)
    make_server(second, port=25566)
    allow_environment(monkeypatch)

    results = server_import.detect_server_directories(root, {str(second.resolve())})

    assert [result["name"] for result in results] == ["survival"]


def test_relative_import_path_is_rejected():
    result = server_import.inspect_server_directory("minecraft")

    assert result["ready"] is False
    assert result["errors"] == ["Use an absolute server path"]


def test_import_page_is_not_captured_by_server_id_route():
    detail = next(
        route for route in web_servers_router.routes
        if route.path == "/servers/{server_id:int}"
    )
    importer = next(
        route for route in web_servers_router.routes
        if route.path == "/servers/import"
    )
    scope = {"type": "http", "method": "GET", "path": "/servers/import"}

    assert detail.matches(scope)[0] is Match.NONE
    assert importer.matches(scope)[0] is Match.FULL
