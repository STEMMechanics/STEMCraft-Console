import pytest

from types import SimpleNamespace

from app import processes
from app.processes import (
    build_java_command,
    normalize_memory,
    register_server,
    resolve_server_jar,
)


def test_build_java_command_keeps_arguments_separate():
    assert build_java_command("4G", "server.jar", '-Dname="Test Server" --add-modules jdk.incubator.vector') == [
        "java", "-Xms4G", "-Xmx4G", "-Dname=Test Server",
        "--add-modules", "jdk.incubator.vector", "-jar", "server.jar", "--nogui",
    ]


def test_build_java_command_supports_separate_initial_and_maximum_memory():
    command = build_java_command("6G", "server.jar", "", "2G")

    assert command[:3] == ["java", "-Xms2G", "-Xmx6G"]


def test_build_java_command_rejects_initial_memory_above_maximum():
    with pytest.raises(ValueError, match="Initial memory"):
        build_java_command("2G", "server.jar", "", "4G")


@pytest.mark.parametrize("memory", ["", "0G", "2GBXX", "-1G", "$(id)"])
def test_build_java_command_rejects_invalid_memory(memory):
    with pytest.raises(ValueError, match="Maximum RAM"):
        build_java_command(memory)


@pytest.mark.parametrize("jar_name", ["../paper.jar", "..\\paper.jar", "/tmp/paper.jar", "paper.txt"])
def test_build_java_command_rejects_unsafe_jar_name(jar_name):
    with pytest.raises(ValueError, match="JAR filename"):
        build_java_command(jar_name=jar_name)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("4GB", "4G"), ("2048mb", "2048M"), ("512 KB", "512K")],
)
def test_memory_units_are_normalized(value, expected):
    assert normalize_memory(value) == expected


def test_server_jar_must_be_a_regular_file_inside_server_directory(tmp_path):
    server_directory = tmp_path / "server"
    server_directory.mkdir()
    jar = server_directory / "paper.jar"
    jar.write_bytes(b"jar")

    assert resolve_server_jar(server_directory, "paper.jar") == jar
    with pytest.raises(ValueError, match="existing JAR"):
        resolve_server_jar(server_directory, "missing.jar")
    with pytest.raises(ValueError, match="existing JAR"):
        resolve_server_jar(server_directory, "../../secret.jar")


def test_server_jar_rejects_symlink_to_external_file(tmp_path):
    server_directory = tmp_path / "server"
    server_directory.mkdir()
    external = tmp_path / "secret.jar"
    external.write_bytes(b"secret")
    (server_directory / "paper.jar").symlink_to(external)

    with pytest.raises(ValueError, match="existing JAR"):
        resolve_server_jar(server_directory, "paper.jar")


@pytest.mark.parametrize(
    "java_args",
    ["-Xmx8G", "-jar other.jar", "@/etc/java.args", "-Dconfig=../../secret"],
)
def test_java_options_cannot_override_managed_values_or_reference_paths(java_args):
    with pytest.raises(ValueError, match="cannot override memory"):
        build_java_command("4G", "paper.jar", java_args)


def test_register_server_rejects_unsafe_systemd_instance():
    server = SimpleNamespace(
        id=1, process_backend="systemd", service_name="bad/name", directory="/srv/server",
        memory="2G", jar_name="paper.jar", java_args="",
    )
    with pytest.raises(ValueError, match="service name"):
        register_server(server)


def test_systemctl_uses_argument_list_without_shell(monkeypatch):
    captured = {}
    monkeypatch.setattr(processes.subprocess, "run", lambda command, **kwargs: captured.update(command=command, kwargs=kwargs))
    config = processes.ServerProcessConfig("systemd", "survival", "/srv/server", "2G", "paper.jar", "")
    processes._systemctl(config, "start")
    assert captured["command"] == [
        "systemctl", "enable", "--now", "stemcraft-server@survival.service",
    ]
    assert "shell" not in captured["kwargs"]


def test_systemctl_stop_disables_instance(monkeypatch):
    captured = {}
    monkeypatch.setattr(processes.subprocess, "run", lambda command, **kwargs: captured.update(command=command))
    config = processes.ServerProcessConfig("systemd", "survival", "/srv/server", "2G", "paper.jar", "")

    processes._systemctl(config, "stop")

    assert captured["command"] == [
        "systemctl", "disable", "--now", "stemcraft-server@survival.service",
    ]


def test_systemd_status_parses_properties_by_name(monkeypatch):
    config = processes.ServerProcessConfig("systemd", "survival", "/srv/server", "2G", "paper.jar", "")
    result = SimpleNamespace(
        returncode=0,
        # systemctl does not guarantee the order of selected properties.
        stdout="MainPID=4321\nActiveState=active\n",
    )
    monkeypatch.setattr(processes, "_systemctl", lambda *args, **kwargs: result)

    status = processes._systemd_status(config)

    assert status == {"running": True, "pid": 4321, "backend": "systemd"}


def test_systemd_status_treats_zero_pid_as_missing(monkeypatch):
    config = processes.ServerProcessConfig("systemd", "survival", "/srv/server", "2G", "paper.jar", "")
    result = SimpleNamespace(returncode=0, stdout="ActiveState=inactive\nMainPID=0\n")
    monkeypatch.setattr(processes, "_systemctl", lambda *args, **kwargs: result)

    status = processes._systemd_status(config)

    assert status == {"running": False, "pid": None, "backend": "systemd"}


def test_process_stats_reuses_psutil_process_for_cpu_deltas(monkeypatch):
    created = []

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid
            self.calls = 0
            created.append(self)

        def cpu_percent(self, interval=None):
            self.calls += 1
            return 0 if self.calls == 1 else 12.5

        def create_time(self):
            return 1000

        def memory_info(self):
            return SimpleNamespace(rss=1024)

        def memory_percent(self):
            return 1.0

    monkeypatch.setattr(processes, "server_status", lambda server_id: {"running": True, "pid": 4321})
    monkeypatch.setattr(processes.psutil, "Process", FakeProcess)
    processes.stats_processes.pop(99, None)
    processes.stats_process_roots.pop(99, None)
    processes.stats_process_started_at.pop(99, None)
    monkeypatch.setattr(processes.time, "time", lambda: 1123)

    processes.server_process_stats(99)
    result = processes.server_process_stats(99)

    assert len(created) == 1
    assert result["cpu_percent"] == 12.5
    assert result["uptime_seconds"] == 123


def test_systemd_process_stats_measure_minecraft_child(monkeypatch):
    class FakeProcess:
        def __init__(self, pid, cpu=0):
            self.pid = pid
            self.cpu = cpu
            self.calls = 0

        def children(self, recursive=False):
            return [minecraft]

        def cpu_percent(self, interval=None):
            self.calls += 1
            return 0 if self.calls == 1 else self.cpu

        def create_time(self):
            return 2000

        def memory_info(self):
            return SimpleNamespace(rss=2048)

        def memory_percent(self):
            return 2.0

    supervisor = FakeProcess(100)
    minecraft = FakeProcess(101, cpu=37.5)
    monkeypatch.setattr(processes, "server_status", lambda server_id: {"running": True, "pid": 100})
    monkeypatch.setattr(processes, "_systemd_config", lambda server_id: object())
    monkeypatch.setattr(processes.psutil, "Process", lambda pid: supervisor)
    processes.stats_processes.pop(1000, None)
    processes.stats_process_roots.pop(1000, None)
    processes.stats_process_started_at.pop(1000, None)
    monkeypatch.setattr(processes.time, "time", lambda: 2125)

    processes.server_process_stats(1000)
    result = processes.server_process_stats(1000)

    assert result["cpu_percent"] == 37.5
    assert result["memory_used"] == 2048
    assert result["uptime_seconds"] == 125
