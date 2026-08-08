import pytest

from types import SimpleNamespace

from app import processes
from app.processes import build_java_command, register_server


def test_build_java_command_keeps_arguments_separate():
    assert build_java_command("4G", "server.jar", '-Dname="Test Server" --add-modules jdk.incubator.vector') == [
        "java", "-Xms4G", "-Xmx4G", "-Dname=Test Server",
        "--add-modules", "jdk.incubator.vector", "-jar", "server.jar", "--nogui",
    ]


@pytest.mark.parametrize("memory", ["", "0G", "2GB", "-1G", "$(id)"])
def test_build_java_command_rejects_invalid_memory(memory):
    with pytest.raises(ValueError, match="Memory"):
        build_java_command(memory)


@pytest.mark.parametrize("jar_name", ["../paper.jar", "/tmp/paper.jar", "paper.txt"])
def test_build_java_command_rejects_unsafe_jar_name(jar_name):
    with pytest.raises(ValueError, match="JAR name"):
        build_java_command(jar_name=jar_name)


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
    assert captured["command"] == ["systemctl", "start", "stemcraft-server@survival.service"]
    assert "shell" not in captured["kwargs"]


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

        def memory_info(self):
            return SimpleNamespace(rss=1024)

        def memory_percent(self):
            return 1.0

    monkeypatch.setattr(processes, "server_status", lambda server_id: {"running": True, "pid": 4321})
    monkeypatch.setattr(processes.psutil, "Process", FakeProcess)
    processes.stats_processes.pop(99, None)
    processes.stats_process_roots.pop(99, None)

    processes.server_process_stats(99)
    result = processes.server_process_stats(99)

    assert len(created) == 1
    assert result["cpu_percent"] == 12.5


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

    processes.server_process_stats(1000)
    result = processes.server_process_stats(1000)

    assert result["cpu_percent"] == 37.5
    assert result["memory_used"] == 2048
